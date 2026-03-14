// sample_arm64.c
#include <stdio.h>

// 简单加法
int add(int a, int b) { return a + b; }

// 循环累加（测试 LOOP 模式识别）
int sum_array(int *arr, int n) {
    int total = 0;
    for (int i = 0; i < n; i++) total += arr[i];
    return total;
}

// 向量化乘加（测试 SIMD 识别）
void fma_loop(float *result, float *a, float *b, float *c, int n) {
    for (int i = 0; i < n; i++)
        result[i] = a[i] * b[i] + c[i];
}

int main(void) {
    int a[3] = {1, 2, 3};
    printf("add(1,2)=%d\n", add(1, 2));
    printf("sum_array=%d\n", sum_array(a, 3));
    float r[3], x[3] = {1, 2, 3}, y[3] = {4, 5, 6}, z[3] = {7, 8, 9};
    fma_loop(r, x, y, z, 3);
    printf("fma_loop[0]=%f\n", r[0]);
    return 0;
}

