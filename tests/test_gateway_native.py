"""Compile the actual gateway C with host stubs to exercise TCP failure boundaries."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GatewayNativeTest(unittest.TestCase):
    def test_partial_writes_and_oversized_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            headers = {
                'esp_err.h': '#pragma once\ntypedef int esp_err_t;\n#define ESP_OK 0\n#define ESP_ERR_NO_MEM 1\n',
                'esp_log.h': '#define ESP_LOGE(...) ((void)0)\n#define ESP_LOGI(...) ((void)0)\n',
                'esp_timer.h': '#include <stdint.h>\nstatic inline int64_t esp_timer_get_time(void){return 1;}\n',
                'freertos/FreeRTOS.h': '#pragma once\ntypedef int BaseType_t;\n#define pdTRUE 1\n#define pdPASS 1\n#define portMAX_DELAY 0\n#define pdMS_TO_TICKS(x) (x)\n',
                'freertos/semphr.h': '#include "FreeRTOS.h"\ntypedef void *SemaphoreHandle_t;\nstatic inline int xSemaphoreTake(SemaphoreHandle_t s,int t){return 1;}\nstatic inline void xSemaphoreGive(SemaphoreHandle_t s){}\nstatic inline SemaphoreHandle_t xSemaphoreCreateMutex(void){return (void*)1;}\n',
                'freertos/task.h': '#include "FreeRTOS.h"\nstatic inline void vTaskDelay(int t){}\nstatic inline int xTaskCreatePinnedToCore(void(*f)(void*),const char*n,int st,void*a,int p,void*h,int c){return pdPASS;}\n',
                'lwip/inet.h': '#include <arpa/inet.h>\n',
                'lwip/sockets.h': '#include <sys/socket.h>\n',
                'lwip/tcp.h': '#include <netinet/tcp.h>\n',
            }
            for name, text in headers.items():
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            fixture = root / 'fixture.c'
            fixture.write_text(r'''
#include <assert.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <string.h>
#include <errno.h>
static int mode, closes;
static const char *incoming;
static size_t offset;
static ssize_t fake_send(int fd,const void *data,size_t size,int flags) {
    if(mode==1){errno=EAGAIN;return -1;}
    if(mode==2)return 3;
    if(mode==3)return 0;
    if(mode==4){errno=ECONNRESET;return -1;}
    return size;
}
static int fake_shutdown(int fd,int how){return 0;}
static int fake_close(int fd){closes++;return 0;}
static ssize_t fake_recv(int fd,void *buffer,size_t size,int flags){
    size_t n=strlen(incoming)-offset;
    if(n>size)n=size;
    memcpy(buffer,incoming+offset,n);offset+=n;return n;
}
#define send fake_send
#define recv fake_recv
#define shutdown fake_shutdown
#define close fake_close
#include "touran_gateway.c"
int main(void){
    s_client_mutex=(void*)1;
    for(mode=0;mode<5;mode++){
        closes=0;s_client_fd=42;
        bool result=send_line_nonblocking("{\"type\":\"health\"}\n");
        assert(result==(mode==0));
        if(mode<2){assert(closes==0);assert(s_client_fd==42);}
        else {assert(closes==1);assert(s_client_fd==-1);}
    }
    char input[1000];memset(input,'x',768);
    strcpy(input+768,"{\"cmd\":\"capture\",\"enable\":false}\n");
    incoming=input;offset=0;mode=0;s_capture=true;s_client_fd=-1;closes=0;
    serve_client(42);assert(s_capture);assert(closes==1);
    strcat(input,"{\"cmd\":\"capture\",\"enable\":false}\n");
    offset=0;s_capture=true;closes=0;
    serve_client(42);assert(!s_capture);assert(closes==1);
    return 0;
}
''')
            binary = root / 'gateway-test'
            subprocess.run(['cc', '-std=c11', '-ffunction-sections', '-fdata-sections',
                            '-I', str(root), '-I', str(ROOT / 'esp32-firmware/main'),
                            str(fixture), '-Wl,--gc-sections', '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=5)


if __name__ == '__main__':
    unittest.main()
