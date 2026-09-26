/* Run CPython inside the branded process, retaining YoonDF.exe in Task Manager.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>

typedef int (__cdecl *python_main)(int, wchar_t **);
typedef void (__cdecl *python_program)(const wchar_t *);

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR tail, int show) {
    static wchar_t executable[32768], library[32768];
    DWORD n=GetModuleFileNameW(NULL,executable,32768);
    if (!n || n>=32768) return 1;
    wcscpy(library,executable);
    wchar_t *slash=wcsrchr(library,L'\\');
    if (!slash) return 1;
    *slash=0;
    if (wcslen(library)+15>=32768) return 1;
    wcscat(library,L"\\python312.dll");
    HMODULE python=LoadLibraryExW(library,NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
    if (!python) goto failed;
    python_main run=(python_main)GetProcAddress(python,"Py_Main");
    python_program set_program=(python_program)GetProcAddress(python,"Py_SetProgramName");
    if (!run || !set_program) goto failed;
    int argc=0;
    wchar_t **argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    if (!argv) goto failed;
    set_program(executable);
    /* Preserve Python's -c/-m options used by multiprocessing and font jobs.
     * python312._pth beside the DLL defines the isolated package paths. */
    int result=run(argc,argv);
    LocalFree(argv);
    /* Native extension cleanup may still reference python312.dll at exit. */
    return result;
failed:
    MessageBoxW(NULL,L"윤DF 실행 환경을 불러오지 못했습니다.\n최신 설치 파일로 다시 설치해 주세요.",L"윤DF",MB_OK|MB_ICONERROR);
    return 1;
}
