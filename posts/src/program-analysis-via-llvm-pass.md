---
title: LLVM Pass与程序分析
date: Feb 23, 2020
---

*注：本文所用LLVM版本为3.8*

## 0. Overview

根据官方介绍，[LLVM](http://llvm.org/) 是一堆模块化的，可复用的编译器以及工具链。LLVM Pass是其中非常重要的一部分，它可以让你对程序进行编译器级别的修改，但是又不需要你真的实现一个编译器。所谓编译器级别的修改——如果你对编译器有所了解的话，就知道编译器首先会通过lexical/syntax analysis将源代码解析成AST（abstract syntax tree，即语法树)，然后对AST进行semantic analysis以及各种各样的optimization，最后生成目标代码。在对AST进行分析的过程中，编译器会对AST进行一次或多次，局部或全局的分析，这些分析被模块化了之后，每个分析往往只负责一个相对独立的功能，这些分析也被称作Compiler Pass。LLVM会将源代码统一表示成LLVM自己定义的IR（intermediate representation，即中间表示），并基于IR生成AST，然后再将AST交给用户，让用户根据自己的需求去写Pass对程序进行分析。

这篇文章主要是关于用LLVM Pass来实现简化版taint analysis（污点分析）的核心部分。

## 1. Taint analysis

Taint analysis可以被看作是信息流分析（Information Flow Analysis）的一种，主要是追踪数据在程序中的走向。具体实现的话，用static analysis（静态分析）或者dynamic analysis（动态分析）都可以。这里主要是用static analysis。我们要实现的简化版taint analysis，目标是找到程序中所有有可能被攻击者控制的变量。下面我尝试简洁地说明什么是taint analysis。

#### 1.1 几个问题

* 为什么要追踪数据在程序中的走向？
    * 这里主要是为了最大程度地识别潜在的恶意输入，从而提高程序的安全性。在现实世界中，攻击者的payload是多种多样的，我们往往无法预知攻击者的payload会以何种形式呈现（无法从形式上防范），但是我们知道许多payload都有一些共同的特征，比如说很多payload经过复杂的转换，最终会作为参数传入`system`函数，并执行恶意指令。通过追踪这些数据的走向，我们可以识别用户的输入是否具有这些特征。换句话说，在程序分析中，用户的原始输入长什么样并不重要，我们在意的是这段输入对于程序运行状态的影响。
* 哪些数据是需要被追踪的
    * 这里我们认为任何用户的输入都是不被信任的，所以任何来自用户的输入都应该被追踪。相似的，任何会被用户的输入影响的数据也都应该被追踪。
* 数据是如何被追踪的
    * “追踪数据”是一个抽象的说法，具体到程序中，我们的做法就是找出程序中可能被攻击者控制的变量，然后监控那些变量是否会被用在某些危险的地方，如`system`函数中。

#### 1.2 几个概念

* source：指（不被信任的）数据的源头，这里我们可以简化为用户的输入。实际上source可以多种多样，任何可能被攻击者利用的输入都可以是source，比如一个配置文件，一个网络请求，或是一段音乐。
* sink：指数据的出口，这里特指比较危险的函数，如C中的`system`（导致command injection）， PHP中的`echo`（导致XSS），等等。
* tainted variable：指在程序中存储（不被信任的）数据的变量，也就是可能被攻击者控制的变量。
* sanitize：指程序中变量从被追踪状态（tainted）到不被追踪状态（untainted）的过程，一般是由特定函数或者重新赋值来完成。比如说下面代码中第一行的`a`处于tainted状态，因为程序对用户输入没有进行任何处理，直接将用户输入作为`echo`的参数会导致XSS；但第三行中的`a`就处于sanitized（untainted）状态，因为此时`a`中的特殊字符被`htmlspecialchars`转义过，XSS攻击在这里失效了。如果我们只关心XSS攻击，那我们就没必要再追踪`a`这个变量了（除非`a`的值在之后又被改变了）。这里的的`htmlspecialchars`函数就可以叫做是XSS的sanitizer。

```php
1 $a = user_input(); // tainted
2 echo $a;
3 $a = htmlspecialchars($a); // not tainted because of sanitization
4 echo $a;
```

## 2. Strategy

#### 2.1 high-level strategy

Taint analysis的难点在于已知source/sink的情况下，在茫茫多的变量中，如何精确地分辨source传过来的数据是否到达了sink。准确度很重要，如果不安全数据没有到达sink，但是你的分析却报了一条警告，那么这条警告就是false positive(FP)；如果不安全数据到达了sink，但是你的分析却报了一条警告，那么这条警告就是true negative(TN)。没有人喜欢FP或是TN，试想一下一个杀毒软件整天报告说你的正常文件是病毒，却又遗漏了真正的病毒。

要追踪不安全数据的传播（taint propagation），其实很简单，变量总是一步一步传播的。比如说变量`a`被tainted了，然后`b = a`，那我们就说`b`也被tainted了，就是这么简单。

Tainted variable的传播方式主要可以分为赋值指令、布尔指令、算数指令、分支指令等。其中值得注意的是布尔指令，布尔指令不是总能传播taintness的。考虑以下代码：

```C
bool a = user_input(); // tainted
bool b = false; // not tainted
bool res1 = a & b; // not tainted
bool res2 = a || b; // still tainted
```

我们可以看到`res1`不再处于tainted状态，而`res2`依然被tainted，背后的原因我这里就不说了。

布尔指令还涉及到追踪的精度问题，考虑以下代码：

```C
uint8_t a = atoi(user_input()); // tainted
uint32_t b = 0xfffffff; // not tainted
b &= a; // tainted, but how?
uint32_t c = b & 0xffff000; // is c tainted?
```

我们可以清楚地意识到第三行的`b`是一个tainted variable，也就意味着它可能被攻击者所控制，根据之前提到的逻辑，`c`当然也应该是tainted的，因为它的值是从`b`里来的。但是事实如此吗？我们注意到`a`的长度是8个bit，而`b`的值是通过与`a`进行&操作得到的，也就是说攻击者至多只能控制`b`低位的8个bit，而`c`的值则完全不受`b`中低位的8个bit影响，所以实际上`c`并不应该被taint。

在下面的实现中，为简便起见，我们不考虑上面提到的布尔指令带来的问题，我们会简单粗暴地认为布尔指令也总是会传播taintness的。

#### 2.2 LLVM-specific strategy

如之前所说，在LLVM中，我们需要和LLVM IR生成出来的AST打交道，所以上述的high-level strategy必须落实到LLVM IR上才行。为了方便起见，这里的具体实现有所不同，上面说的是我们要先找到tainted data，然后追踪这些data如何在程序中传播。这里我使用的相反的策略，我打算找到程序中所有的常量（constant），那么除常量之外的，都是静态分析下无法确定具体值的变量，换句话说，它们的值是需要外部输入来确定的，也就是潜在的，可能被攻击者控制的值。
我们要关注的IR指令有以下几种：

- `StoreInst`：语法是`store src, dst`，将src的值存到dst中，如果src的值是tainted的，那么dst的值也是tainted的
- `LoadInst`：语法是`dst = load src`，将src的值存到dst中，如果src的值是tainted的，那么dst的值也是tainted的
- `CmpInst`：用于比较数字的大小，包括整数与实数，假如该指令的一个或两个操作数被tainted，那么其结果也被tainted
- `CastInst`：用于类型转换，如果被转换的变量是tainted，那么转换后的变量也是tainted的
- `BinaryOperator`：所有二元操作符，包括算术指令，布尔指令等，虽然之前提到过布尔指令的问题，但是这里为了简化，直接定义成，如果两个操作数中有一个或两个是tainted的，那么它们的结果也是tainted的

LLVM中IR是以不同的的scope组织起来的，常用的scope从大到小排列如下：Module > Function > BasicBlock > Instruction。为了进行上述分析，我们可以通过遍历的方式来查看每一条instruction，看这些指令是不是我们所关心的，但是也有更好的办法。回忆上面说到的AST，LLVM提供了不同scope的visitor（visitor pattern是compiler里最常见的设计模式之一），我们需要用到的是[InstVisitor](https://llvm.org/doxygen/classllvm_1_1InstVisitor.html)，顾名思义，InstVisitor会遍历AST中的每一条Instruction，我们只需重写我们关心的指令所对应的visit函数。


## 3. Implementation

首先我们需要做准备工作，即编译LLVM，这里我们使用LLVM3.8，编译大约需要20-40分钟不等。编译完成后，文章后面提到的所有LLVM相关程序如`opt`，`llvm-dis`等，都可以在`llvm/build/bin`目录下找到。

```sh
mkdir llvm; cd llvm
wget http://releases.llvm.org/3.8.0/llvm-3.8.0.src.tar.xz
wget http://releases.llvm.org/3.8.0/cfe-3.8.0.src.tar.xz
tar xf llvm-3.8.0.src.tar.xz
tar xf cfe-3.8.0.src.tar.xz
mv llvm-3.8.0.src src
mv cfe-3.8.0.src src/tools/clang
mkdir build; cd build
cmake ../src
make
```



然后开始写代码，首先我们需要新建一个struct并继承InstVisitor，并建立一个`std::set`来存储所有的常量。

```cpp
struct TaintInstVisitor : public InstVisitor<TaintInstVisitor> {
  TaintInstVisitor() {}
  ~TaintInstVisitor() {}
  set<Value*> const_vars;
}

```

另外，我们需要一个判定常量的方法，这里我们使用LLVM自带的`isa<Constant>()`方法来检测目标变量是否是常量，如果一个变量是常量，那么我们就将这个常量加入上面定义的`const_vars`中；如果一个变量的值是从常量派生而来的，那我们也将它加入`const_vars`中，所以我们检测一个变量是否是常量的函数可以写成如下形式：

```cpp
struct TaintInstVisitor : public InstVisitor<TaintInstVisitor> {
  // ...
  bool is_constant (Value* v) {
    return (const_vars.find(v) != const_vars.end()) || (isa<Constant>(v));
  }
}

```

接下来我们实现如何判断一个变量是否由常量派生而来。首先是`StoreInst`，判断方式很简单，如果`src`是常量，那么`dst`也是常量

```cpp
struct TaintInstVisitor : public InstVisitor<TaintInstVisitor> {
  // ...
  void visitStoreInst(StoreInst &I) {
    // syntax: store src, dst
    // if src is a constant, then dst is a constant
    Value *op1 = I.getOperand(0); // src
    if (is_constant(op1)) {
      Value *operand2 = I.getOperand(1); // dst
      const_vars.insert(operand2);
    }
  }
}
```

然后是`LoadInst`与`CastInst`，同样的如果`src`是常量，那么`dst`也是常量。在这里必须要提一下LLVM精巧的设计，在LLVM中，各种`Instruction`是继承自`Value`的，你可以通过`Insturction`的各种方法来得到关于这条指令的各种信息，而这个`Instruction`本身的值则代表了这条指令的返回值。比如说，`load src`，我们知道这条指令是将`src`的值赋给另一个变量，但是这个变量怎么表示呢？在LLVM里，`load src`这条指令本身就代表了被赋值的那个变量。在单操作数的指令中，如`LoadInst`与`CastInst`，这条指令本身就代表了那个被赋值的变量。

```cpp
struct TaintInstVisitor : public InstVisitor<TaintInstVisitor> {
  // ...
  void visitLoadInst(LoadInst &I) {
    // syntax: dst = load src
    // if src is a const, then dst is a const
    Value *op = I.getOperand(0); // src
    if (is_constant(op)) { // src is a const
      const_vars.insert(&I); // dst is also a const
    }
  }
  void visitCastInst(CastInst &I) {
    // syntax: dst = load src
    Value *op = I.getOperand(0);
    if (is_constant(op)) {
      const_vars.insert(&I);
    }
  }
}
```

剩下的则是各种二元操作符，包括比较，算术，布尔指令，等等，我们可以用一个统一的函数来处理它们。这里我们简单粗暴地认为只有当二元操作符的两个操作数都是常量的时候，我们才认为这个被赋值的变量也是一个常量。

```cpp
struct TaintInstVisitor : public InstVisitor<TaintInstVisitor> {
  // ...
  void visitCmpInst(CmpInst &I) {
    handle_binaryOp(I);
  }

  void visitBinaryOperator(BinaryOperator &I) {
    handle_binaryOp(I);
  }

  void handle_binaryOp(Instruction& I) {
    Value *op1 = I.getOperand(0);
    Value *op2 = I.getOperand(1);
    // TODO: actually boolean operator don't follow: &&, ||, &, |
    if (is_constant(op1) && is_constant(op2)) {
      const_vars.insert(&I);
    }
  }
}
```

最后我们创建一个`TaintInstVisitor`的实例，并将其运行于这个Module，最后我们将检测到的所有常量打印出来：

```cpp
struct Hello : public ModulePass {
  struct TaintInstVisitor : public InstVisitor<TaintInstVisitor> {
    // ...
  }
  virtual bool runOnModule(Module &M) {
    TaintInstVisitor tv;
    tv.visit(M);
    set<Value*> const_vars = tv.get_const_vars();
    for (auto it = const_vars.begin(); it != const_vars.end(); it++) {
      errs() << *static_cast<Instruction*>(*it) << '\n';
    }
    return true;
  }
}
```

## 4. Run 

写完了Pass，下面就要开始运行了。首先我们要知道LLVM Pass运行于LLVM的bitcode上，一般我们通过使用clang编译来得到bitcode：

```bash
clang -emit-llvm -o a.out.bc -c test.c
```

而我则偏好用[wllvm](https://github.com/travitch/whole-program-llvm/)来得到bitcode，wllvm是Python写的，你可以通过pip来安装它，然后用如下命令取得bitcode：

```bash
wllvm test.bc
extract-bc a.out # generate bitcode file called a.out.bc
```

wllvm的优势在于，当你在编译一个拥有许多源文件的project时，你也可以通过上面这两条简单的指令来获取整个项目的bitcode。

获取bitcode之后，我们使用LLVM的opt来运行它，这里我们写的Pass叫做Hello，我们可以使用如下命令来运行这个Pass

```bash
opt -load LLVMHello.so -Hello < a.out.bc > /dev/null
```

## 5. Verify

下面我们通过下面这个简单的程序来验证一下，其中只有`b`是常量，其他变量都是可以被攻击者控制的。

```c
#include <stdio.h>

int main(int argc, char** argv) {
  int a = argc;
  int b = 1;
  int c = a + b;
  printf("%d\n", c);
}
```

使用上面提到的方法运行Pass，打印如下结果：

```llvm
  %b = alloca i32, align 4
  %2 = load i32, i32* %b, align 4
```

这说明该程序中共有两个变量的值为常量，第一个是`b`，第二个是`%2`。其中`%2`是一个临时变量，它的值是通过load变量b的值得到的，也就是说它的值完全等于`b`的值。由此来看，输出结果与我们之前的分析相符。

我们可以通过`llvm-dis`将bitcode转换为IR，再来验证一下Pass输出的正确性。

```bash
llvm-dis a.out.bc
```

上述命令会生成IR文件，名为`a.out.ll`，主要内容如下：

```llvm
@.str = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1

; Function Attrs: nounwind uwtable
define i32 @main(i32 %argc, i8** %argv) #0 {
entry:
  %argc.addr = alloca i32, align 4
  %argv.addr = alloca i8**, align 8
  %a = alloca i32, align 4
  %b = alloca i32, align 4
  %c = alloca i32, align 4
  store i32 %argc, i32* %argc.addr, align 4
  store i8** %argv, i8*** %argv.addr, align 8
  %0 = load i32, i32* %argc.addr, align 4
  store i32 %0, i32* %a, align 4
  store i32 1, i32* %b, align 4 ; %b is a constant
  %1 = load i32, i32* %a, align 4
  %2 = load i32, i32* %b, align 4 ; %2 is a constant
  %add = add nsw i32 %1, %2
  store i32 %add, i32* %c, align 4
  %3 = load i32, i32* %c, align 4
  %call = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @.str, i32 0, i32 0), i32 %3)
  ret i32 0
}
```

通过查看IR我们可以发现，Pass的输出结果是正确的，在这个程序里，只有`%b`和`%2`的值是常量，而其他的值都是潜在的可以被攻击者控制的值。

## 6. More about LLVM

利用LLVM Pass还可以做很多很多事，简单的比如说生成call graph，control flow graph之类的，或者找出代码中所有的循环；稍微复杂点的，就不只是分析，可能会涉及到instrumentation，也就是利用LLVM更改程序行为，比如说在源代码中引入一个新的函数，并在所有特定类型的指令之后都插入该函数的调用。

当然LLVM也不是无所不能的，比如它不适用于没有源代码的项目，对于这种情况，或许使用来自Intel的Pin来做动态分析显得更为合适。


## 7. Taint analysis and others


#### 7.1 Implicit flows

文章写到这里，看起来taint analysis已经很强大了，可事实上依旧存在它难以处理的情况，比如implicit flows。

考虑以下代码：

```c
x	=	user_input(); // tainted
y	=	x; // tainted
if (y == 0) { // tainted
	z	=	2; // not tainted
} else {
	z	=	1; // not tainted
}	
system(z);
```

沿用我们之前写的analysis，我们会得出`x`和`y`是tainted的而`z`并不是tainted的结论，进而得出“`system(z)`是安全的”这样一个结论。但是事实真的如此吗？我们注意到当`y`的值为0的时候，`z`的值必定是2；而当`y`的值不为0时，`z`的值必定为1。换句话说，`z`的值是由`y`的值来决定的，不同于上面提到的任何一种方式，这种方式是间接的，通过控制流（control flow）而非数据流（data flow）来决定的。

这时候，我们实际上陷入了一个进退两难的境地。激进的做法是，如果决定分支的变量与用户输入有关，则taint该分支中所有的变量，这会导致over-taint，很多不该被taint的变量最后也被taint了；保守的做法是，放弃在taint analysis中检测implicit flows，也就是说，在上面的代码中，`z`将不会被标记为tainted。不过，无论选择那一种做法，都是不完美的，都会导致分析的结果出现偏差。

所以就没有更好的办法了吗？说实话，我也并不是很清楚。不过如果你有兴趣，我会建议你google一下“causality inference taint analysis”，也许你会发现比taint analysis更好的方法。

