// ConfigurationInkScapePourTrotec.cpp
// Configure Inkscape pour la découpeur laser Trotec Speedy 100.
// Compilation : Visual Studio 2019/2022, projet Win32 Application (Unicode).

#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "shell32.lib")

#include "framework.h"
#include "ConfigurationInkScapePourTrotec.h"
#include <winhttp.h>
#include <shlobj.h>
#include <string>
#include <vector>
#include <fstream>

#define WM_INSTALL_DONE (WM_APP + 1)

// ── Globals ──────────────────────────────────────────────────────────────────

static HINSTANCE    g_hInst;
static bool         g_installSuccess = false;
static std::wstring g_installError;
static HWND         g_hwndProgress   = nullptr;

// ── Chemins ───────────────────────────────────────────────────────────────────

static std::wstring AppDataInkscape()
{
    wchar_t buf[MAX_PATH];
    SHGetFolderPathW(nullptr, CSIDL_APPDATA, nullptr, 0, buf);
    return std::wstring(buf) + L"\\inkscape";
}

static std::wstring TempDir()
{
    wchar_t buf[MAX_PATH];
    ::GetTempPathW(MAX_PATH, buf);
    return buf;
}

// ── Arborescence ──────────────────────────────────────────────────────────────

static void DeleteTree(const std::wstring& dir)
{
    std::wstring pat = dir + L"\\*";
    WIN32_FIND_DATAW fd;
    HANDLE h = FindFirstFileW(pat.c_str(), &fd);
    if (h == INVALID_HANDLE_VALUE) return;
    do {
        if (!wcscmp(fd.cFileName, L".") || !wcscmp(fd.cFileName, L"..")) continue;
        std::wstring full = dir + L"\\" + fd.cFileName;
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            DeleteTree(full);
            RemoveDirectoryW(full.c_str());
        } else {
            SetFileAttributesW(full.c_str(), FILE_ATTRIBUTE_NORMAL);
            DeleteFileW(full.c_str());
        }
    } while (FindNextFileW(h, &fd));
    FindClose(h);
}

static bool CopyTree(const std::wstring& src, const std::wstring& dst)
{
    CreateDirectoryW(dst.c_str(), nullptr);
    std::wstring pat = src + L"\\*";
    WIN32_FIND_DATAW fd;
    HANDLE h = FindFirstFileW(pat.c_str(), &fd);
    if (h == INVALID_HANDLE_VALUE) return false;
    bool ok = true;
    do {
        if (!wcscmp(fd.cFileName, L".") || !wcscmp(fd.cFileName, L"..")) continue;
        std::wstring s = src + L"\\" + fd.cFileName;
        std::wstring d = dst + L"\\" + fd.cFileName;
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
            ok &= CopyTree(s, d);
        else
            ok &= (CopyFileW(s.c_str(), d.c_str(), FALSE) != 0);
    } while (FindNextFileW(h, &fd));
    FindClose(h);
    return ok;
}

// ── Téléchargement HTTPS ──────────────────────────────────────────────────────
// Suit automatiquement les redirections (ex. github.com → codeload.github.com).

static bool DownloadHttps(const wchar_t* host, const wchar_t* path,
                           const std::wstring& destFile, std::wstring& err)
{
    HINTERNET hSess = WinHttpOpen(L"ConfigInkscape/1.0",
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, nullptr, nullptr, 0);
    if (!hSess) { err = L"WinHTTP : initialisation échouée."; return false; }

    DWORD proto = WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2;
    WinHttpSetOption(hSess, WINHTTP_OPTION_SECURE_PROTOCOLS, &proto, sizeof(proto));

    HINTERNET hConn = WinHttpConnect(hSess, host, INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!hConn) {
        WinHttpCloseHandle(hSess);
        err = L"WinHTTP : connexion impossible."; return false;
    }

    HINTERNET hReq = WinHttpOpenRequest(hConn, L"GET", path,
        nullptr, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
    if (!hReq) {
        WinHttpCloseHandle(hConn); WinHttpCloseHandle(hSess);
        err = L"WinHTTP : création de la requête échouée."; return false;
    }

    DWORD redir = WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS;
    WinHttpSetOption(hReq, WINHTTP_OPTION_REDIRECT_POLICY, &redir, sizeof(redir));

    if (!WinHttpSendRequest(hReq, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
            WINHTTP_NO_REQUEST_DATA, 0, 0, 0) ||
        !WinHttpReceiveResponse(hReq, nullptr))
    {
        DWORD e = GetLastError();
        WinHttpCloseHandle(hReq); WinHttpCloseHandle(hConn); WinHttpCloseHandle(hSess);
        err = L"Téléchargement échoué (erreur WinHTTP " + std::to_wstring(e) + L").";
        return false;
    }

    DWORD status = 0, sz = sizeof(status);
    WinHttpQueryHeaders(hReq, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
        nullptr, &status, &sz, nullptr);
    if (status != 200) {
        WinHttpCloseHandle(hReq); WinHttpCloseHandle(hConn); WinHttpCloseHandle(hSess);
        err = L"Serveur GitHub : code HTTP " + std::to_wstring(status) + L".";
        return false;
    }

    std::ofstream file(destFile, std::ios::binary);
    if (!file) {
        WinHttpCloseHandle(hReq); WinHttpCloseHandle(hConn); WinHttpCloseHandle(hSess);
        err = L"Impossible de créer le fichier temporaire."; return false;
    }

    std::vector<char> buf(65536);
    DWORD avail = 0, nread = 0;
    while (WinHttpQueryDataAvailable(hReq, &avail) && avail > 0) {
        if (buf.size() < avail) buf.resize(avail);
        WinHttpReadData(hReq, buf.data(), avail, &nread);
        file.write(buf.data(), nread);
    }

    file.close();
    WinHttpCloseHandle(hReq); WinHttpCloseHandle(hConn); WinHttpCloseHandle(hSess);
    return true;
}

// ── Commande cachée ───────────────────────────────────────────────────────────

static bool RunHidden(const std::wstring& cmdLine, std::wstring& err)
{
    STARTUPINFOW si    = { sizeof(si) };
    si.dwFlags         = STARTF_USESHOWWINDOW;
    si.wShowWindow     = SW_HIDE;
    PROCESS_INFORMATION pi = {};
    std::wstring cmd   = cmdLine;   // CreateProcessW exige un buffer modifiable

    if (!CreateProcessW(nullptr, &cmd[0], nullptr, nullptr,
                        FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi))
    {
        err = L"Impossible de lancer la commande (err=" +
              std::to_wstring(GetLastError()) + L").";
        return false;
    }
    WaitForSingleObject(pi.hProcess, 300000);   // timeout 5 min
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    if (code != 0) {
        err = L"Commande échouée (code=" + std::to_wstring(code) + L").";
        return false;
    }
    return true;
}

// ── Thread d'installation ─────────────────────────────────────────────────────

static DWORD WINAPI InstallThread(LPVOID)
{
    std::wstring tmp = TempDir();
    std::wstring zip = tmp + L"InkscapeConfig.zip";
    std::wstring ext = tmp + L"InkscapeConfig_ext";

    // 1. Télécharger l'archive ZIP complète du repo
    if (!DownloadHttps(
            L"github.com",
            L"/FrankSAURET/InkscapePourTrotec/archive/refs/heads/main.zip",
            zip, g_installError))
    {
        PostMessage(g_hwndProgress, WM_INSTALL_DONE, 0, 0);
        return 0;
    }

    // 2. Extraire avec PowerShell (disponible sur Windows 10+)
    std::wstring ps =
        L"powershell.exe -NoProfile -NonInteractive -Command "
        L"\"Expand-Archive -LiteralPath '" + zip +
        L"' -DestinationPath '" + ext + L"' -Force\"";

    if (!RunHidden(ps, g_installError)) {
        g_installError = L"Extraction ZIP : " + g_installError;
        DeleteFileW(zip.c_str());
        PostMessage(g_hwndProgress, WM_INSTALL_DONE, 0, 0);
        return 0;
    }
    DeleteFileW(zip.c_str());

    // 3. Valider la présence du dossier inkscape dans l'archive extraite
    std::wstring src = ext + L"\\InkscapePourTrotec-main\\inkscape";
    if (GetFileAttributesW(src.c_str()) == INVALID_FILE_ATTRIBUTES) {
        g_installError = L"Dossier 'inkscape' introuvable dans l'archive extraite.\n"
                         L"La structure du dépôt GitHub a peut-être changé.";
        DeleteTree(ext); RemoveDirectoryW(ext.c_str());
        PostMessage(g_hwndProgress, WM_INSTALL_DONE, 0, 0);
        return 0;
    }

    // 4. Téléchargement validé → effacer %APPDATA%\inkscape puis copier
    std::wstring dst = AppDataInkscape();
    CreateDirectoryW(dst.c_str(), nullptr);
    DeleteTree(dst);

    if (!CopyTree(src, dst)) {
        g_installError = L"Erreur lors de la copie des fichiers vers %APPDATA%\\inkscape.";
        DeleteTree(ext); RemoveDirectoryW(ext.c_str());
        PostMessage(g_hwndProgress, WM_INSTALL_DONE, 0, 0);
        return 0;
    }

    // 5. Nettoyage des fichiers temporaires
    DeleteTree(ext);
    RemoveDirectoryW(ext.c_str());

    g_installSuccess = true;
    PostMessage(g_hwndProgress, WM_INSTALL_DONE, 1, 0);
    return 0;
}

// ── Fenêtre de confirmation ───────────────────────────────────────────────────

static int g_confirmResult = IDCANCEL;

static LRESULT CALLBACK ConfirmProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    switch (msg) {
    case WM_CREATE:
    {
        HFONT fnt = (HFONT)GetStockObject(DEFAULT_GUI_FONT);
        auto mk = [&](const wchar_t* cls, const wchar_t* txt, DWORD style,
                      int x, int y, int w, int h, int id)
        {
            HWND c = CreateWindowW(cls, txt, WS_CHILD | WS_VISIBLE | style,
                x, y, w, h, hwnd, (HMENU)(UINT_PTR)id, g_hInst, nullptr);
            SendMessage(c, WM_SETFONT, (WPARAM)fnt, TRUE);
        };
        mk(L"STATIC",
            L"Voulez-vous configurer InkScape pour la découpeuse\r\n"
            L"laser Trotec Speedy 100 ?\r\n\r\n"
            L"Attention : toute configuration préalable d'Inkscape\r\n"
            L"sera perdue.",
            SS_LEFT, 20, 18, 395, 105, 0);
        mk(L"BUTTON", L"Annuler", BS_PUSHBUTTON,    70,  145, 120, 30, IDCANCEL);
        mk(L"BUTTON", L"OK",     BS_DEFPUSHBUTTON,  250, 145, 120, 30, IDOK);
        return 0;
    }
    case WM_COMMAND:
        g_confirmResult = LOWORD(wp);
        DestroyWindow(hwnd);
        return 0;
    case WM_CLOSE:
        g_confirmResult = IDCANCEL;
        DestroyWindow(hwnd);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

// ── Fenêtre de progression ────────────────────────────────────────────────────

static LRESULT CALLBACK ProgressProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    switch (msg) {
    case WM_CREATE:
    {
        HFONT fnt = (HFONT)GetStockObject(DEFAULT_GUI_FONT);
        HWND c = CreateWindowW(L"STATIC",
            L"Téléchargement et installation en cours,\r\nveuillez patienter…",
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            20, 28, 370, 50, hwnd, nullptr, g_hInst, nullptr);
        SendMessage(c, WM_SETFONT, (WPARAM)fnt, TRUE);
        SetCursor(LoadCursor(nullptr, IDC_WAIT));
        return 0;
    }
    case WM_INSTALL_DONE:
        DestroyWindow(hwnd);
        return 0;
    case WM_CLOSE:
        return 0;   // fermeture bloquée pendant l'installation
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

// ── Utilitaire ────────────────────────────────────────────────────────────────

static HWND CreateCenteredWindow(const wchar_t* cls, const wchar_t* title,
                                  WNDPROC proc, int w, int h)
{
    WNDCLASSW wc     = {};
    wc.lpfnWndProc   = proc;
    wc.hInstance     = g_hInst;
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1);
    wc.lpszClassName = cls;
    wc.hCursor       = LoadCursor(nullptr, IDC_ARROW);
    wc.hIcon         = LoadIconW(g_hInst,
                           MAKEINTRESOURCEW(IDI_CONFIGURATIONINKSCAPEPOURTROTEC));
    RegisterClassW(&wc);

    int x = (GetSystemMetrics(SM_CXSCREEN) - w) / 2;
    int y = (GetSystemMetrics(SM_CYSCREEN) - h) / 2;

    return CreateWindowExW(WS_EX_DLGMODALFRAME | WS_EX_APPWINDOW,
        cls, title, WS_CAPTION | WS_SYSMENU,
        x, y, w, h, nullptr, nullptr, g_hInst, nullptr);
}

static void RunMsgLoop()
{
    MSG msg;
    while (GetMessageW(&msg, nullptr, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
}

// ── Point d'entrée ────────────────────────────────────────────────────────────

int APIENTRY wWinMain(_In_     HINSTANCE hInstance,
                      _In_opt_ HINSTANCE,
                      _In_     LPWSTR,
                      _In_     int)
{
    g_hInst = hInstance;

    // 1. Boîte de confirmation
    HWND hwndConfirm = CreateCenteredWindow(
        L"ConfirmDlg",
        L"Configuration Inkscape — Trotec Speedy 100",
        ConfirmProc, 455, 220);
    ShowWindow(hwndConfirm, SW_SHOW);
    UpdateWindow(hwndConfirm);
    RunMsgLoop();

    if (g_confirmResult != IDOK) return 0;

    // 2. Fenêtre de progression + thread d'installation
    g_hwndProgress = CreateCenteredWindow(
        L"ProgressDlg",
        L"Configuration Inkscape — Trotec Speedy 100",
        ProgressProc, 430, 130);
    ShowWindow(g_hwndProgress, SW_SHOW);
    UpdateWindow(g_hwndProgress);

    HANDLE hThread = CreateThread(nullptr, 0, InstallThread, nullptr, 0, nullptr);
    RunMsgLoop();
    WaitForSingleObject(hThread, INFINITE);
    CloseHandle(hThread);

    // 3. Résultat
    if (g_installSuccess) {
        MessageBoxW(nullptr,
            L"Inkscape est maintenant configuré pour travailler\n"
            L"avec la Trotec Speedy 100.",
            L"Configuration réussie",
            MB_OK | MB_ICONINFORMATION);
    } else {
        std::wstring txt = L"La configuration a échoué.\n\nErreur :\n" + g_installError;
        MessageBoxW(nullptr, txt.c_str(),
            L"Erreur de configuration", MB_OK | MB_ICONERROR);
    }

    return 0;
}
