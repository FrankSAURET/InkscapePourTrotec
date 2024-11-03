# Engrenage
-----
Version 2024.1
For inkscape V 1.x
-----
Gears extension for tracing involute gears and metric pitch gears (belt pulley); allows spokes, center cross, metric module, best evolute shape.

Initially, copy of inkscape-gears-dev (https://github.com/jnweiger/inkscape-gears-dev).

- 2024-10-25 | 2024.1 : Ajout du tracé de roue de fixation pour les servomoteurs. Changement de versionnage. Flancs pour roue de type T.
- 2024-07-20 | 1.4 : Ajout du tracé de poulie au pas métrique. Retouche des explications. Ajout de schémas.
- 2024-06-22 | 1.3 : Ajout de couleurs pour l'ordre de découpe. Séparation en plusieurs objet pour faciliter la retouche et la recolorisation.
- 2024-06-18 | 1.2 : Ajout de la possibilité de choisir la forme du trou (rectangulaire, ronde ou empreinte de servo) et de choisir les dimensions du trou. Ajout de la possibilité de choisir une empreinte pour le trou du servo. Les empreintes sont placées dans le fichier engrenage.ini
- 2024-04-21 | 1.1 : traduction en français. Modification de la couleur en cas d'undercut. Modification du deddendum pour qu'il fasse 1,25 fois l'addendum.

Usage
-----
Copy the .inx, .py, svg, png and ini files in to your Inkscape extensions directory (usually on windows C:\Users\username\AppData\Roaming\inkscape\extensions or %appdata%\inkscape\extensions). 
The actual directory can be found under Preferences/System.

ini file can be modified to add hole shape. If you do this, you must add the name in the dropdown list into the inx file (under 62 line). The name in value attrib must be the same in the ini file (name between []).

Restart inkscape.

The extension will be available under "Extensions > Formes > Engrenage...".

All code is offered under Licence : GPLV2.