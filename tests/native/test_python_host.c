#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "../../packaging/python_host.c"
static const wchar_t *exe=L"C:\\윤재영 폴더\\윤DF\\runtime\\YoonDF.exe";
static wchar_t *arguments[]={L"YoonDF.exe",L"-c",L"multiprocessing.spawn(...)",L"--multiprocessing-fork",NULL};
static int calls,errors,missing,exit_code;
DWORD GetModuleFileNameW(HANDLE h,wchar_t *out,DWORD n){wcscpy(out,exe);return wcslen(out);}
HMODULE LoadLibraryExW(const wchar_t *path,HANDLE h,DWORD flags){
    assert(wcscmp(path,L"C:\\윤재영 폴더\\윤DF\\runtime\\python312.dll")==0);
    assert(flags==LOAD_WITH_ALTERED_SEARCH_PATH);return missing?NULL:(HMODULE)1;
}
static void program(const wchar_t *name){assert(wcscmp(name,exe)==0);}
static int run(int argc,wchar_t **argv){assert(argc==4 && argv==arguments);calls++;return exit_code;}
void *GetProcAddress(HMODULE module,const char *name){return strcmp(name,"Py_Main")==0?(void *)run:(void *)program;}
wchar_t *GetCommandLineW(void){return L"test";}
wchar_t **CommandLineToArgvW(const wchar_t *line,int *argc){*argc=4;return arguments;}
HANDLE LocalFree(HANDLE value){assert(value==arguments);return NULL;}
int MessageBoxW(void *a,const wchar_t *message,const wchar_t *title,unsigned flags){errors++;return 1;}
int main(void){
    assert(wWinMain(0,0,L"",1)==0 && calls==1);
    exit_code=7;assert(wWinMain(0,0,L"",1)==7 && calls==2);
    missing=1;assert(wWinMain(0,0,L"",1)==1 && errors==1 && calls==2);
    puts("PASS: branded host absolute DLL path, Unicode paths, interpreter arguments, return status and missing runtime");
}
