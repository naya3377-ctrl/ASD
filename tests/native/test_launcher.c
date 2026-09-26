/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Run the real launcher source with explicit OS doubles. This verifies dispatch
 * and argument handling; it does not claim Windows installation execution. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../../packaging/launcher.c"
static const wchar_t *module = L"C:\\Users\\테스트 사용자\\비책 PDF\\BichaekPDF.exe";
static const wchar_t *choice;
static int missing_runtime, spawn_fails, launches, messages, closes, legacy;
static wchar_t started[32768], cwd[32768], cmd[32768];
DWORD GetModuleFileNameW(HANDLE h, wchar_t *s, DWORD n) {
    wcsncpy(s,module,n); return (DWORD)wcslen(module);
}
DWORD GetFileAttributesW(const wchar_t *s) {
    if (wcsstr(s,L"current.ini")) return choice ? 0 : INVALID_FILE_ATTRIBUTES;
    if (legacy && wcsstr(s,L"\\runtime\\YoonDF.exe")) return INVALID_FILE_ATTRIBUTES;
    return missing_runtime ? INVALID_FILE_ATTRIBUTES : 0;
}
DWORD GetPrivateProfileStringW(const wchar_t *a,const wchar_t *b,const wchar_t *c,wchar_t *s,DWORD n,const wchar_t *f) {
    wcsncpy(s,choice,n-1); s[n-1]=0; return (DWORD)wcslen(s);
}
int CreateProcessW(const wchar_t *p,wchar_t *c,void *a,void *b,int inherit,DWORD flags,void *env,const wchar_t *d,STARTUPINFOW *si,PROCESS_INFORMATION *pi) {
    ++launches; wcscpy(started,p); wcscpy(cmd,c); wcscpy(cwd,d);
    assert(si->cb==sizeof(*si)); assert(!inherit); return !spawn_fails;
}
int MessageBoxW(void *a,const wchar_t *s,const wchar_t *t,unsigned f) { ++messages; return 1; }
int CloseHandle(HANDLE h) { ++closes; return 1; }
static void reset(const wchar_t *release) {
    choice=release; launches=messages=closes=missing_runtime=spawn_fails=legacy=0;
    started[0]=cwd[0]=cmd[0]=0;
}
int main(void) {
    wchar_t args[]=L"\"C:\\문서 폴더\\한글.pdf\" \"D:\\두 번째.pdf\"";
    reset(L"0.5.1-2"); assert(wWinMain(0,0,args,1)==0);
    assert(wcscmp(cwd,L"C:\\Users\\테스트 사용자\\비책 PDF\\versions\\0.5.1-2")==0);
    assert(wcsstr(started,L"\\versions\\0.5.1-2\\runtime\\YoonDF.exe"));
    assert(wcsstr(cmd,L"\\versions\\0.5.1-2\\main.py\" "));
    assert(wcscmp(cmd+wcslen(cmd)-wcslen(args),args)==0);
    assert(launches==1 && closes==2 && messages==0);
    reset(NULL); assert(wWinMain(0,0,L"",1)==0);
    assert(wcscmp(cwd,L"C:\\Users\\테스트 사용자\\비책 PDF")==0);
    assert(!wcsstr(started,L"versions"));
    reset(L"0.9.1-1");legacy=1;assert(wWinMain(0,0,args,1)==0);
    assert(wcsstr(started,L"\\runtime\\pythonw.exe"));
    const wchar_t *bad[]={L"",L"..",L"..\\other",L"0.5.1/other",L"C:\\other",L"0.5.1-1\\..",L"0.5.1-1 ",L"0.5.1-1:stream"};
    for (size_t i=0;i<sizeof(bad)/sizeof(*bad);++i) {
        reset(bad[i]); assert(wWinMain(0,0,L"",1)==1);
        assert(!launches && messages==1);
    }
    wchar_t long_name[140]; wmemset(long_name,L'1',139); long_name[139]=0;
    reset(long_name); assert(wWinMain(0,0,L"",1)==1); assert(!launches);
    reset(L"0.5.1-1"); missing_runtime=1;
    assert(wWinMain(0,0,L"",1)==1 && !launches && messages==1);
    reset(L"0.5.1-1"); spawn_fails=1;
    assert(wWinMain(0,0,L"",1)==1 && launches==1 && messages==1);
    puts("PASS: version/repair selection, legacy layout, Unicode/spaces/arguments, invalid pointer, missing runtime, spawn failure");
}
