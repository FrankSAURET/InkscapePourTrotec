# Boite_brique
-----
Version 2021.1
For inkscape V 1.x
-----

Creates a tabbed box with kerf setting for tight fits. Or dimples for press fits.

- set dimensions in various units,
- width, depth, height, material thickness,
- choose number of tabs for each dimension,
- include corners or not,
- kerf adjustable - if tight fit required, or
- can use dimples for pressure fits for wood etc (rounds or triangles), or
- can set zero kerf and use minimal material to create.

In all cases - uses minimal lines to optimise for laser cutting.

The kerf was not correctly adjusted, making it impossible to nest parts if the kerf was wide. So I modified this extension.
I also added a no-cover function and the choice of the kerf by the choice of the material.
The original extension is here : https://inkscape.org/~Neon22/%E2%98%85lasercut-tabbed-box

Usage
-----

Copy the .inx and .py files in to your Inkscape extensions directory (usually on windows C:\Users\username\AppData\Roaming\inkscape\extensions or %appdata%\inkscape\extensions). 
The actual directory can be found under Preferences/System.

Restart inkscape.

The extension will be available under "Extensions > Découpe Laser > Boite « Brique »...".

All code is offered under Licence : GPLV2.