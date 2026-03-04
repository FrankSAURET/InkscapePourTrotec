def main():

    import os
    import tkinter as tk
    from i18n import setup as i18n_setup

    # Traduction : gettext lit automatiquement la variable LANGUAGE
    # définie par Inkscape selon ses préférences de langue.
    localedir = os.path.join(os.path.dirname(__file__), 'locale')
    i18n_setup(localedir)

    # Imports APRÈS la configuration de la traduction
    from gui.main_window import MainWindow
    from core.config import Config

    config = Config.load()
    root = tk.Tk()
    min_w, min_h = 600, 580
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws // 2) - (min_w // 2)
    y = (hs // 2) - (min_h // 2)
    root.geometry(f"{min_w}x{min_h}+{x}+{y}")
    root.resizable(False, False)
    _app = MainWindow(root, config)
    root.mainloop()

if __name__ == "__main__":
    main()
