#include <stdio.h>
#include <stdlib.h>

typedef struct Node {
    int data;
    struct Node *next;
} linked_list;

void dump(linked_list* head) {
  while (head) {
    printf("%d, %p, %p\n", head->data, head, head->next);
    head = head->next;
  }
}

int main() {
  int i;
  linked_list* head = NULL;
  linked_list* cursor = NULL;
  linked_list* to_rm = NULL;
  for (i = 0; i < 5; i++) {
    linked_list* node = (linked_list*)malloc(sizeof(linked_list));
    node->data = i + 1;
    node->next = NULL;
    if (i == 1) to_rm = node;
    if (!head){
      head = cursor = node; 
    } else {
      cursor->next = node;
      cursor = cursor->next;
    }
  }
  dump(head);
  linked_list** indirect = &head;
  while ((*indirect) != to_rm) {
    indirect = &(*indirect)->next;
    /**indirect = (*indirect)->next;*/
    printf("%p, %p\n", indirect, *indirect);
  }
  *indirect = to_rm->next;
  dump(head);
}



