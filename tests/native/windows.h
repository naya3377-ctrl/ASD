/* Minimal Win32 test doubles for the launcher control flow, not an emulator. */
#ifndef BICHAEK_TEST_WINDOWS_H
#define BICHAEK_TEST_WINDOWS_H
#include <stddef.h>
#include <stdint.h>
#include <wchar.h>
#define WINAPI
#define __cdecl
#define LOAD_WITH_ALTERED_SEARCH_PATH 8
#define FALSE 0
#define MB_OK 0
#define MB_ICONERROR 16
#define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
#define _snwprintf swprintf
typedef uint32_t DWORD;
typedef void *HINSTANCE;
typedef void *HANDLE;
typedef void *HMODULE;
typedef wchar_t *PWSTR;
typedef struct { DWORD cb; } STARTUPINFOW;
typedef struct { HANDLE hProcess, hThread; } PROCESS_INFORMATION;
DWORD GetModuleFileNameW(HANDLE, wchar_t *, DWORD);
DWORD GetFileAttributesW(const wchar_t *);
DWORD GetPrivateProfileStringW(const wchar_t *,const wchar_t *,const wchar_t *,wchar_t *,DWORD,const wchar_t *);
int CreateProcessW(const wchar_t *,wchar_t *,void *,void *,int,DWORD,void *,const wchar_t *,STARTUPINFOW *,PROCESS_INFORMATION *);
int MessageBoxW(void *,const wchar_t *,const wchar_t *,unsigned);
int CloseHandle(HANDLE);
HMODULE LoadLibraryExW(const wchar_t *,HANDLE,DWORD);
void *GetProcAddress(HMODULE,const char *);
wchar_t *GetCommandLineW(void);
HANDLE LocalFree(HANDLE);
#endif
