<head>

<script>
    document.title = "简易IPC的实现"
</script>

<script>
    document.getElementsByTagName("head")[0].innerHTML += "<link rel='shortcut icon' href='../imgs/icon.png' type='image/x-icon'/>";
</script>
  
<meta name="google-site-verification" content="vAQHjUuTdIGja16wxCarfwIS4qQ4BgKN0xUbLfdHVmY" />
  
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-116308654-1"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'UA-116308654-1');
</script>

</head>

<div class="inner">

# 简易IPC的实现

## 0. 总览

IPC（Inter-Process Communication），进程间通信，至少两个进程或线程间传送数据或信号的技术。进程是计算机系统分配资源的最小单位(严格说来是线程)。每个进程都有自己的一部分独立的系统资源，彼此是隔离的。为了能使不同的进程互相访问资源并进行协调工作，才有了进程间通信。这里使用mailbox来实现多对多（many-to-many）的进程间通信。

## 1. 准备

操作系统中进程的状态一般分为三类：就绪（ready）、阻塞（waiting）与运行（running）。其中阻塞又可以分为等待某种资源而阻塞（如等待I/O）或等待时间流逝而阻塞（如调用wait）。

<img src="../imgs/task_states.png" alt="kernel_task_states" style="height: 300px;"/>



</div>