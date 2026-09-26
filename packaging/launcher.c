/* SPDX-License-Identifier: AGPL-3.0-or-later */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>

/* Only a single release-directory name is accepted, never an arbitrary path. */
static int release_name_ok(const wchar_t *name) {
    if (name[0] < L'0' || name[0] > L'9') return 0;
    for (const wchar_t *p = name; *p; ++p)
        if (!((*p >= L'0' && *p <= L'9') || *p == L'.' || *p == L'-'))
            return 0;
    return 1;
}

int WINAPI wWinMain(HINSTANCE a, HINSTANCE b, PWSTR args, int show) {
    /* Static buffers avoid overflowing the default Windows thread stack. */
    static wchar_t dir[32768], python[32768], script[32768], command[32768];
    static wchar_t config[32768], release[128], selected[32768];
    DWORD n = GetModuleFileNameW(NULL, dir, 32768);
    if (!n || n >= 32768) return 1;
    wchar_t *slash = wcsrchr(dir, L'\\');
    if (!slash) return 1;
    *slash = 0;
    if (_snwprintf(config, 32768, L"%ls\\current.ini", dir) < 0) return 1;
    if (GetFileAttributesW(config) != INVALID_FILE_ATTRIBUTES) {
        DWORD count = GetPrivateProfileStringW(L"Install", L"Release", L"",
                                               release, 128, config);
        if (!count || count >= 127 || !release_name_ok(release) ||
            _snwprintf(selected, 32768, L"%ls\\versions\\%ls", dir, release) < 0)
            goto invalid_install;
        wcscpy(dir, selected);
    }
    /* Without current.ini this also runs a legacy/portable payload directly. */
    if (_snwprintf(python, 32768, L"%ls\\runtime\\YoonDF.exe", dir) < 0) return 1;
    /* Existing version selectors may still point to a pre-0.9.2 release. */
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES &&
        _snwprintf(python, 32768, L"%ls\\runtime\\pythonw.exe", dir) < 0) return 1;
    if (_snwprintf(script, 32768, L"%ls\\main.py", dir) < 0 ||
        _snwprintf(command, 32768, L"\"%ls\" \"%ls\" %ls", python, script, args) < 0)
        return 1;
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(script) == INVALID_FILE_ATTRIBUTES)
        goto invalid_install;
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si);
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        goto invalid_install;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;

invalid_install:
    MessageBoxW(NULL, L"윤DF 실행 파일을 찾거나 열 수 없습니다.\n"
                      L"최신 설치 프로그램으로 다시 설치해 주세요.",
                L"윤DF", MB_OK | MB_ICONERROR);
    return 1;
}
