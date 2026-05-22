#include <stdio.h>

int global_var = 100;

int calculate_sum(int a, int b) {
    int result = a + b;
    return result;
}

int main() {
    int x = 10;
    float y = 3.14;
    char grade = 'A';
    char message[] = "Hello, World!";
    
    if (x > 5) {
        y = y * 2.0;
        printf("Y doubled: %f\n", y);
    } else {
        printf("X is too small\n");
    }
    
    for (int i = 0; i < 5; i++) {
        x = x + i;
        printf("Iteration %d: x = %d\n", i, x);
    }
    
    int sum = calculate_sum(x, 20);
    printf("Final sum: %d\n", sum);
    
    return 0;
}