from __future__ import annotations

import tkinter as tk
from tkinter import font
import os
from typing import Any, Callable
from i18n import _
import json

class InstalledExtensionsListWidget(tk.Frame):
    """
    Canvas + Frame scrollable, lignes alternées, sélection,
    molette, et icône upgradable à droite sur la ligne version.
    """

    def __init__(self, parent: tk.Widget, installed_extensions: list[dict[str, Any]], outdated_extensions: list[dict[str, Any]], on_select: Callable[[dict[str, Any]], None] | None = None, *args: Any, **kwargs: Any) -> None:
        super().__init__(parent, *args, **kwargs)
        self.installed_extensions = installed_extensions
        self.outdated_extensions = outdated_extensions
        self.on_select = on_select

        # Charger config.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            template = config_data.get('Template', [{}])[0]
            self.colors: dict[str, str] = template.get('colors', {})
            self.format_text: dict[str, Any] = template.get('format_text', {})
        except Exception as e:
            print("[Maj] Erreur chargement config.json:", e)
            self.colors: dict[str, str] = {}
            self.format_text: dict[str, Any] = {}

        def get_color(key: str) -> str:
            return self.colors.get(key, "#FF00FF")
        self.get_color = get_color

        def get_font_cfg(key: str, fallback: tuple[Any, ...]) -> tuple[Any, ...]:
            val = self.format_text.get(key)
            return tuple(val) if val else fallback
        self.get_font = get_font_cfg

        # Canvas + Scrollbar
        self.canvas = tk.Canvas(self,
                                bg=self.get_color('fond_ligne_paire'),
                                highlightthickness=0,
                                bd=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar ttk avec style personnalisé
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.Vertical.TScrollbar',
            background=self.get_color('scrollbar_slider'),
            troughcolor=self.get_color('scrollbar_trough'),
            bordercolor=self.get_color('scrollbar_trough'),
            arrowcolor=self.get_color('scrollbar_arrow'),
            lightcolor=self.get_color('scrollbar_trough'),
            darkcolor=self.get_color('scrollbar_trough'),
            relief='flat')
        style.map('Custom.Vertical.TScrollbar',
            background=[('active', self.get_color('scrollbar_slider_hover'))]
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style='Custom.Vertical.TScrollbar')  # type: ignore[arg-type]
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Frame interne
        self.inner = tk.Frame(self.canvas, bg=self.get_color('fond_ligne_paire'))
        self.inner_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        # Fix largeur/marge
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Molette
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # type: ignore[arg-type]
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # type: ignore[arg-type]
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # type: ignore[arg-type]

        # Polices
        self.font_name   = font.Font(self, self.get_font('font_bold', ("Arial", 11, "bold")))
        self.font_author = font.Font(self, self.get_font('font_author', ("Arial", 10, "italic")))
        self.font_desc   = font.Font(self, self.get_font('font_desc', ("Arial", 11)))
        self.font_ver    = font.Font(self, self.get_font('font_litle', ("Arial", 9)))
        self.font_warning    = font.Font(self, self.get_font('font_warning', ("Arial", 10, "italic")))

        self._wrap_width = 500

        self.rows: list[tuple[tk.Frame, dict[str, Any], str]] = []          # (row_frame, ext, original_bg)
        self.selected_rows: list[tk.Frame] | None = None

        # Icône upgradable
        self._upgradable_icon = None
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'upgradable2.png')
        if os.path.exists(icon_path):
            self._upgradable_icon = tk.PhotoImage(file=icon_path)

        self._populate()

    # --- géométrie / scroll ------------------------------------------------

    def _on_inner_configure(self, event: tk.Event[tk.Frame]) -> None:
        # scrollregion
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event[tk.Canvas]) -> None:
        # largeur du frame interne = largeur du canvas
        self.canvas.itemconfig(self.inner_window, width=event.width)
        self._wrap_width = max(100, event.width - 30)
        # mettre à jour les wraplength
        for row, _ext, _original_bg in self.rows:
            for w in row.winfo_children():
                if hasattr(w, "_is_desc"):
                    w.configure(wraplength=self._wrap_width)  # type: ignore[call-overload]

    def _on_mousewheel(self, event: tk.Event[tk.Canvas]) -> None:
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # --- contenu -----------------------------------------------------------


    def _populate(self) -> None:
        # Ajout du panneau danger et du label d'avertissement en haut de la liste
        warning_frame = tk.Frame(self.inner, bg=self.get_color('fond_warning'))
        warning_frame.pack(fill="x", padx=5, pady=(5, 5), anchor="e")

        # Chargement icône panneau danger
        danger_icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'Danger32.png')
        if os.path.exists(danger_icon_path):
            danger_icon = tk.PhotoImage(file=danger_icon_path)
        else:
            danger_icon = None

        if danger_icon:
            tk.Label(warning_frame, image=danger_icon, bg=self.get_color('fond_warning')).pack(side="left", padx=(5, 20))
            # Conserver la référence pour éviter le garbage collection
            setattr(warning_frame, 'danger_icon', danger_icon)

            tk.Label(warning_frame,
                text=_("Attention : seules les extensions avec un fichier Info.json sont listées !"),
                font=self.get_font('font_bold', ("Arial", 11, "bold")),
                fg=self.get_color('text_version'),
                bg=self.get_color('fond_warning'),
                wraplength=350,
                justify="left").pack(side="left")

        for idx, ext in enumerate(self.installed_extensions):
            local_version = ext.get('version', '?')
            online_txt = ""
            upgradable = False

            for outdated in self.outdated_extensions:
                if outdated.get('name') == ext.get('name'):
                    upgradable = True
                    online_txt = _(" | Version en ligne : {version}").format(version=outdated.get('online_version'))
                    break
            else:
                online_txt = _(" - À jour")

            bg_color = (
                self.get_color('fond_ligne_paire')
                if idx % 2 == 0
                else self.get_color('fond_ligne_impaire')
            )

            row_title = tk.Frame(self.inner, bg=bg_color)
            row_title.pack(fill="x", expand=True)

            row_description = tk.Frame(self.inner, bg=bg_color)
            row_description.pack(fill="x", expand=True)

            row_version = tk.Frame(self.inner, bg=bg_color)
            row_version.pack(fill="x", expand=True)

            self.rows.append((row_title, ext, bg_color))
            self.rows.append((row_description, ext, bg_color))
            self.rows.append((row_version, ext, bg_color))

            # ? Ligne 1
            tk.Label(row_title,
                     text=ext.get('name', '?'),
                     font=self.font_name,
                     bg=bg_color,
                     fg=self.get_color('text_sombre')).pack(side="left")

            tk.Label(row_title,
                     text=_(" par "),
                     font=self.font_author,
                     bg=bg_color,
                     fg=self.get_color('text_by')).pack(side="left")

            tk.Label(row_title,
                     text=ext.get('author', '?'),
                     font=self.font_author,
                     bg=bg_color,
                     fg=self.get_color('text_author')).pack(side="left")

            # ? Ligne 2
            if ext.get("repos", "") == "https://github.com/FrankSAURET/Maj":
                # Ligne 1 : description courte
                desc_label = tk.Label(row_description,
                                      text=ext.get("short_description", ""),
                                      font=self.font_desc,
                                      bg=bg_color,
                                      fg=self.get_color('text_desc'),
                                      wraplength=self._wrap_width,
                                      justify="left")
                setattr(desc_label, '_is_desc', True)
                desc_label.pack(side="top", anchor="w")
                # Ligne 2 : message d'avertissement
                msg = _("« M à j » ne peut pas être mis à jour par elle même. Pour la mettre à jour allez dans le dépôt :")
                github_maj_url = "https://github.com/FrankSAURET/Maj"
                warning_label = tk.Label(
                    row_description,
                    text=msg,
                    font=self.get_font('font_warning', ("Arial", 10, "italic")),
                    bg=bg_color,
                    fg=self.get_color('text_highlight'),
                    anchor="w",
                    justify="left",
                    wraplength=self._wrap_width,
                    padx=20
                )
                warning_label.pack(side="top", anchor="w")
                # Ligne 3 : lien cliquable seul
                link_label = tk.Label(
                    row_description,
                    text=github_maj_url,
                    font=self.get_font('font_warning', ("Arial", 10, "underline")),
                    bg=bg_color,
                    fg=self.get_color('text_lien'),
                    cursor="hand2",
                    padx=40
                )
                link_label.pack(side="top", anchor="w")
                link_label.config(state="normal")
                def open_github_url(event: tk.Event[tk.Label], url: str = github_maj_url) -> None:
                    import webbrowser
                    try:
                        webbrowser.open_new_tab(url)
                    except Exception as ex:
                        print("[Maj] Erreur ouverture navigateur:", ex)
                link_label.bind("<Button-1>", open_github_url)
                link_label.bind("<ButtonRelease-1>", open_github_url)
            else:
                desc_label = tk.Label(row_description,
                                      text=ext.get("short_description", ""),
                                      font=self.font_desc,
                                      bg=bg_color,
                                      fg=self.get_color('text_desc'),
                                      wraplength=self._wrap_width,
                                      justify="left")
                setattr(desc_label, '_is_desc', True)
                desc_label.pack(side="left", anchor="w")

            # ? Ligne 3 : texte à gauche, icône à droite
            left_frame = tk.Frame(row_version, bg=bg_color)
            left_frame.pack(side="left", fill="x", expand=True)

            tk.Label(row_version,
                     text=_("(Version installée: {local_version}{online_txt})").format(local_version=local_version, online_txt=online_txt),
                     font=self.font_ver,
                     bg=bg_color,
                     fg=self.get_color('text_version')).pack(side="left")

            if upgradable and self._upgradable_icon is not None:
                tk.Label(row_version,
                         image=self._upgradable_icon,
                         bg=bg_color).pack(side="right", padx=5)

            # clic sélection
            for row in (row_title, row_description, row_version):
                row.bind("<Button-1>", lambda e, ext=ext: self._select_ext(ext))
                for w in row.winfo_children():
                    w.bind("<Button-1>", lambda e, ext=ext: self._select_ext(ext))

    # --- sélection ---------------------------------------------------------

    def _select_ext(self, ext: dict[str, Any]) -> None:
        if self.selected_rows:
            for row, _ext2, original_bg in self.rows:
                if row in self.selected_rows:
                    row.config(bg=original_bg)
                    for w in row.winfo_children():
                        w.configure(bg=original_bg)  # type: ignore[call-overload]

        rows = [row for row, ext2, _original_bg in self.rows if ext2 is ext]
        self.selected_rows = rows

        for row in rows:
            row.config(bg=self.get_color('fond_selected_ext'))
            for w in row.winfo_children():
                w.configure(bg=self.get_color('fond_selected_ext'))  # type: ignore[call-overload]

        if self.on_select:
            self.on_select(ext)
