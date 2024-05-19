#!/usr/bin/env/python
'''
Copyright (C)2011 Mark Schafer <neon.mark(a)gmaildotcom>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This    program    is    distributed in the    hope    that    it    will    be    useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
'''

# Build a tabbed box for lasercutting with tight fit, and minimal material use options.
# User defines:
# - internal or external dimensions,
# - number of tabs,
# - amount lost to laser (kerf),
# - include corner cubes or not,
# - dimples, or perfect fit (accounting for kerf).
# - If zero kerf it will be perfectly packed for minimal laser cuts and material size.

### Todo
#  add option to pack multiple boxes (if zero kerf) - new tab maybe?
#  add option for little circles at sharp corners for acrylic
#  annotations: - add overlap value as markup - Ponoko annotation color
#  choose colours from a dictionary

### Versions
#  0.1 February 2011 - basic lasercut box with dimples etc
#  0.2 changes to unittouu for Inkscape 0.91
#  0.3 Option to avoid half-sized tabs at corners. <juergen@fabmail.org>
#  0.4 Add option for lid or not
#  0.5 Modify tab for adjust kerf (increase tab size)[Frank SAURET 05-05-2021]

__version__ = "0.5"

#from math import *
import sys
import inkex
from simplepath import *
from lxml import etree

class LasercutBox(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)
        self.arg_parser.add_argument("-i", "--int_ext",
                        type=inkex.Boolean,
                        dest="int_ext", default=False,
                        help="Are the Dimensions for External or Internal sizing.")
        self.arg_parser.add_argument("-x", "--width",
                        type=float,
                        dest="width", default=50.0,
                        help="The Box Width - in the X dimension")
        self.arg_parser.add_argument("-y", "--height",
                        type=float,
                        dest="height", default=30.0,
                        help="The Box Height - in the Y dimension")
        self.arg_parser.add_argument("-z", "--depth",
                        type=float,
                        dest="depth", default=15.0,
                        help="The Box Depth - in the Z dimension")
        self.arg_parser.add_argument("-t", "--thickness",
                        type=float,
                        dest="thickness", default=3.0,
                        help="Material Thickness - critical to know")
        self.arg_parser.add_argument("-u", "--units",
                        type=str,
                        dest="units", default="cm",
                        help="The unit of the box dimensions")
        self.arg_parser.add_argument("-c", "--corners",
                        type=inkex.Boolean,
                        dest="corners", default=True,
                        help="The corner cubes can be removed for a different look")
        self.arg_parser.add_argument("-H", "--halftabs",
                        type=inkex.Boolean,
                        dest="halftabs", default=True,
                        help="Start/End with half-sized tabs - Avoid with very small tabs")
        self.arg_parser.add_argument("-p", "--ntab_W",
                        type=int,
                        dest="ntab_W", default=11,
                        help="Number of tabs in Width")
        self.arg_parser.add_argument("-q", "--ntab_H",
                        type=int,
                        dest="ntab_H", default=11,
                        help="Number of tabs in Height")
        self.arg_parser.add_argument("-r", "--ntab_D",
                        type=int,
                        dest="ntab_D", default=6,
                        help="Number of tabs in Depth")
        #Added by Frank SAURET 13-12-2018
        self.arg_parser.add_argument("-C", "--aveccouvercle",
                        type=inkex.Boolean,
                        dest="aveccouvercle", default=False,
                        help="Box is closed or not")
        self.arg_parser.add_argument("-b", "--bymaterial",
                        type=inkex.Boolean,
                        dest="bymaterial", default=False,
                        help="Are kerf define by material")
        self.arg_parser.add_argument("-o", "--materiaux",
                        type=float,
                        dest="materiaux", default=0.0,
                        help="Kerf size define by material")
        #deddA by Frank SAURET 13-12-2018
        self.arg_parser.add_argument("-k", "--kerf_size",
                        type=float,
                        dest="kerf_size", default=0.0,
                        help="Kerf size - amount lost to laser for this material. 0 = loose fit")
        self.arg_parser.add_argument("-d", "--dimples",
                        type=inkex.Boolean,
                        dest="dimples", default=False,
                        help="Add dimples for press fitting wooden materials")
        self.arg_parser.add_argument("-s", "--dstyle",
                        type=inkex.Boolean,
                        dest="dstyle", default=False,
                        help="Dimples can be triangles(cheaper) or half rounds(better)")
        self.arg_parser.add_argument("-g", "--linewidth",
                        type=inkex.Boolean,
                        dest="linewidth", default=False,
                        help="Use the kerf value as the drawn line width")
        #  Added by Frank SAURET 12-12-2018
        self.arg_parser.add_argument("-f", "--forcingseparation",
                        type=inkex.Boolean,
                        dest="forcingseparation", default=False,
                        help="Forcing the separation of the panels")
        #  deddA by Frank SAURET 12-12-2018
        self.arg_parser.add_argument("--tab",
                        type=str, 
                        dest="tab", 
                        default="use",
                        help="The selected UI-tab when OK was pressed")
        #internal useful variables
        self.stroke_width  = 0.1 #default for visiblity
        self.line_style = {'stroke':          '#0000FF', # Ponoko blue
                           'fill':            'none',
                           'stroke-width':    self.stroke_width,
                           'stroke-linecap':  'butt',
                           'stroke-linejoin': 'miter'}

    def annotation(self, x, y, text):
        """ Draw text at this location
         - change to path
         - use annotation color        """
        pass
            
    def thickness_line(self, dimple, vert_horiz, pos_neg):
        """ called to draw dimples (also draws simple lines if no dimple)
             - pos_neg is 1, -1 for direction
             - vert_horiz is v or h                """
        if dimple and self.kerf > 0.0: # we need a dimple
            # size is radius = kerf
            # short line, half circle, short line
            #[ 'C', [x1,y1, x2,y2, x,y] ]  x1 is first handle, x2 is second
            self.decalage_dimple0=0
            self.decalage_dimple1=self.decalage
            self.decalage_dimple3=2*self.decalage
            self.decalage_dimple4=3*self.decalage            
            lines = []
            radius = self.kerf
            if self.thick - 2 * radius < 0.2:  # correct for large dimples(kerf) on small thicknesses
                radius = (self.thick - 0.2) / 2
                short = 0.1
            else:
                short = self.thick/2 - radius
            if vert_horiz == 'v': # §vertical line
                # first short line
                lines.append(['v', [pos_neg*short]])
                # half circle
                if pos_neg == 1: # only the DH_sides need reversed tabs to interlock
                    if self.dimple_tri:
                        lines.append(['l', [radius, pos_neg*radius]])
                        lines.append(['l', [-radius, pos_neg*radius]])
                    else:
                        lines.append(['c', [radius, 0, radius, pos_neg*2*radius, 0, pos_neg*2*radius]])                
                else:
                    if self.dimple_tri:
                        lines.append(['l', [-radius, pos_neg*radius]])
                        lines.append(['l', [radius, pos_neg*radius]])
                    else:
                        lines.append(['c', [-radius, 0, -radius, pos_neg*2*radius, 0, pos_neg*2*radius]])
                # last short line
                lines.append(['v', [pos_neg*short]])
            else: # §horizontal line
                # first short line
                lines.append(['h', [pos_neg*short]])
                # half circle
                if self.dimple_tri:
                    lines.append(['l', [pos_neg*radius, radius]])
                    lines.append(['l', [pos_neg*radius, -radius]])
                else:
                    lines.append(['c', [0, radius, pos_neg*2*radius, radius, pos_neg*2*radius, 0]])
                # last short line
                lines.append(['h', [pos_neg*short]])
            return lines
        
        # No dimple - so much easier
        else: # return a straight v or h line same as thickness
            self.decalage_dimple0=self.decalage
            self.decalage_dimple1=2 * self.decalage
            self.decalage_dimple3=self.decalage
            self.decalage_dimple4=2*self.decalage            
            if vert_horiz == 'v':
                return [ ['v', [pos_neg*self.thick]] ]
            else:
                return [ ['h', [pos_neg*self.thick]] ]


    def draw_WH_lid(self, startx, starty, boxCover, boxSide, masktop=False):
        """ Return an SVG path for the top or bottom of box
             - the Width * Height dimension                    """
        line_path = []
        line_path.append(['M', [startx, starty]])
        
        # * Trace le dessus de la boite sans languettes
        if boxSide in "Top" and not boxCover:
            line_path.append(['m', [-self.thick, -self.thick]])
            line_path.append(['h', [self.boxW+self.thick*2]])
            line_path.append(['v', [self.boxH+self.thick*2]])
            line_path.append(['h', [-self.boxW-self.thick*2]])
            line_path.append(['v', [-self.boxH-self.thick*2-self.kerf/2]])
        else:
            # $ top row of tabs 
            if masktop and self.kerf ==0.0 and not self.forcing_separation: # don't draw top for packing with no extra cuts
                line_path.append(['m', [self.boxW,0]])
            else:
                if not self.ht: line_path.append(['h', [self.boxW/self.Wtabs/4]])
                for i in range(int(self.Wtabs)):
                    line_path.append(['h', [self.boxW/self.Wtabs/4-self.decalage_dimple0]])#1> 0
                    for l in self.thickness_line(self.dimple, 'v', -1):
                        line_path.append(l)
                    line_path.append(['h', [self.boxW/self.Wtabs/2 +self.decalage_dimple1]])#2>1
                    line_path.append(['v', [self.thick]])
                    line_path.append(['h', [self.boxW/self.Wtabs/4-self.decalage]])
                if not self.ht: line_path.append(['h', [self.boxW/self.Wtabs/4]])
            # $ right hand vertical drop
            if not self.ht: line_path.append(['v', [self.boxH/self.Htabs/4 ]])
            for i in range(int(self.Htabs)):
                line_path.append(['v', [self.boxH/self.Htabs/4 - self.decalage]])
                line_path.append(['h', [self.thick]])
                line_path.append(['v', [self.boxH/self.Htabs/2 + self.decalage_dimple1]])#2>1
                for l in self.thickness_line(self.dimple, 'h', -1):
                    line_path.append(l)
                line_path.append(['v', [self.boxH/self.Htabs/4 - self.decalage_dimple0]])#1>0
            if not self.ht: line_path.append(['v', [self.boxH/self.Htabs/4 ]])
            # $ bottom row (in reverse)
            if not self.ht: line_path.append(['h', [-self.boxW/self.Wtabs/4]])
            for i in range(int(self.Wtabs)):
                line_path.append(['h', [-self.boxW/self.Wtabs/4+self.decalage ]])
                line_path.append(['v', [self.thick]])
                line_path.append(['h', [-self.boxW/self.Wtabs/2 -self.decalage_dimple1]])#2>1
                for l in self.thickness_line(self.dimple, 'v', -1):
                    line_path.append(l)
                line_path.append(['h', [-self.boxW/self.Wtabs/4+self.decalage_dimple0]])#1>0
            if not self.ht: line_path.append(['h', [-self.boxW/self.Wtabs/4]])
            # $ up the left hand side
            if not self.ht: line_path.append(['v', [-self.boxH/self.Htabs/4 ]])
            for i in range(int(self.Htabs)):
                line_path.append(['v', [-self.boxH/self.Htabs/4 +self.decalage_dimple0]])#1>0
                for l in self.thickness_line(self.dimple, 'h', -1):
                    line_path.append(l)
                line_path.append(['v', [-self.boxH/self.Htabs/2 -self.decalage_dimple1]])#2>1
                line_path.append(['h', [self.thick]])
                line_path.append(['v', [-self.boxH/self.Htabs/4+self.decalage ]])
            line_path.append(['v', [-self.pf/2 ]])   #line_path.append(['v', [-self.pf/2 ]]) 
            if not self.ht: line_path.append(['v', [-self.boxH/self.Htabs/4 ]])
        
        
        return line_path


    def draw_WD_side(self, startx, starty, boxCover, boxSide, mask=False, corners=True):
        """ Return an SVG path for the long side of box
             - the Width * Depth dimension                    """
        # Draw side of the box (placed below the lid)
        line_path = []
        # $ top row of tabs
        if corners:
            line_path.append(['M', [startx - self.thick, starty]])
            line_path.append(['v', [-self.thick]])
            line_path.append(['h', [self.thick]])
        else:
            line_path.append(['M', [startx, starty]])
            line_path.append(['v', [-self.thick]])
        #
        # if fit perfectly - don't draw double line  modify by Frank SAURET 12-12-2018
        if boxSide in "Back" and not boxCover:
            if self.kerf == 0.0 and not self.forcing_separation:
                if corners:
                    line_path.append(['m', [self.boxW+self.thick,0]])
                else:
                    line_path.append(['m', [self.boxW,0]])
            else:       
                if corners:
                    line_path.append(['h', [self.boxW+self.thick]])
                else:
                    line_path.append(['h', [self.boxW]])
        else:
            if self.kerf > 0.0 or self.forcing_separation:
                if not self.ht: line_path.append(['h', [self.boxW/self.Wtabs/4]])          
                for i in range(int(self.Wtabs)):
                    line_path.append(['h', [self.boxW/self.Wtabs/4 + self.decalage]])
                    line_path.append(['v', [self.thick]])
                    line_path.append(['h', [self.boxW/self.Wtabs/2 - self.decalage_dimple1]])
                    for l in self.thickness_line(self.dimple, 'v', -1):
                        line_path.append(l)
                    line_path.append(['h', [self.boxW/self.Wtabs/4 + self.decalage_dimple0 ]])
                if not self.ht: line_path.append(['h', [self.boxW/self.Wtabs/4]])
                if corners: line_path.append(['h', [self.thick]])
            else: # move to skipped drawn lines
                if corners:    
                    line_path.append(['m', [self.boxW + self.thick, 0]])
                else:
                    line_path.append(['m', [self.boxW, 0]])
        #
        line_path.append(['v', [self.thick]])
        if not corners: line_path.append(['h', [self.thick]])
        # $  RHS
        if not self.ht: line_path.append(['v', [self.boxD/self.Dtabs/4]])
        for i in range(int(self.Dtabs)):
            line_path.append(['v', [self.boxD/self.Dtabs/4 + self.decalage_dimple0]])
            for l in self.thickness_line(self.dimple, 'h', -1):
                line_path.append(l)
            line_path.append(['v', [self.boxD/self.Dtabs/2 - self.decalage_dimple1 ]])
            line_path.append(['h', [self.thick]])
            line_path.append(['v', [self.boxD/self.Dtabs/4 + self.decalage]])
        if not self.ht: line_path.append(['v', [self.boxD/self.Dtabs/4 ]])
        #
        if corners:
            line_path.append(['v', [self.thick]])
            line_path.append(['h', [-self.thick]])
        else:
            line_path.append(['h', [-self.thick]])
            line_path.append(['v', [self.thick]])
        # $ base
        if boxSide in "Front" and not boxCover:
            if corners:
                line_path.append(['h', [-self.boxW]])
            else:
                line_path.append(['h', [-self.boxW]])
        else:
            if not self.ht: line_path.append(['h', [-self.boxW/self.Wtabs/4]])
            for i in range(int(self.Wtabs)):
                line_path.append(['h', [-self.boxW/self.Wtabs/4 -self.decalage_dimple0]])
                for l in self.thickness_line(self.dimple, 'v', -1):
                    line_path.append(l)
                line_path.append(['h', [-self.boxW/self.Wtabs/2+self.decalage_dimple1]])
                line_path.append(['v', [self.thick]])
                line_path.append(['h', [-self.boxW/self.Wtabs/4-self.decalage ]])
            if not self.ht: line_path.append(['h', [-self.boxW/self.Wtabs/4]])
        #
        if corners:
            line_path.append(['h', [-self.thick]])
            line_path.append(['v', [-self.thick]])
        else:
            line_path.append(['v', [-self.thick]])
            line_path.append(['h', [-self.thick]])
        # $ LHS
        if not self.ht: line_path.append(['v', [-self.boxD/self.Dtabs/4 ]])
        for i in range(int(self.Dtabs)):
            line_path.append(['v', [-self.boxD/self.Dtabs/4 -self.decalage]])
            line_path.append(['h', [self.thick]])
            line_path.append(['v', [-self.boxD/self.Dtabs/2+self.decalage_dimple1 ]])
            for l in self.thickness_line(self.dimple, 'h', -1):
                line_path.append(l)
            line_path.append(['v', [-self.boxD/self.Dtabs/4-self.decalage_dimple0]])
        if not self.ht: line_path.append(['v', [-self.boxD/self.Dtabs/4]])
        #
        line_path.append(['h', [self.pf/2 ]])
        if not corners: line_path.append(['h', [self.thick]])
        return line_path


    def draw_HD_side(self, startx, starty, boxCover, boxSide, corners, mask=False):
        """ Return an SVG path for the short side of box
             - the Height * Depth dimension                    """
        line_path = []
        # $ top row of tabs
        line_path.append(['M', [startx, starty]])
        line_path.append(['h', [self.thick]])
        if not self.ht: line_path.append(['h', [self.boxD/self.Dtabs/4]])
        for i in range(int(self.Dtabs)):
            line_path.append(['h', [self.boxD/self.Dtabs/4-self.decalage ]])
            line_path.append(['v', [-self.thick]])
            line_path.append(['h', [self.boxD/self.Dtabs/2+self.decalage_dimple1 ]])
            for l in self.thickness_line(self.dimple, 'v', 1):
                line_path.append(l)
            line_path.append(['h', [self.boxD/self.Dtabs/4 -self.decalage_dimple0]])
        if not self.ht: line_path.append(['h', [self.boxD/self.Dtabs/4]])
        line_path.append(['h', [self.thick]])
        # $ Right row of tabs or line
        if not self.ht: line_path.append(['v', [self.boxH/self.Htabs/4 ]])
        if boxSide in "Right" and not boxCover:
            if self.ht:
                line_path.append(['v', [self.boxH]])
            else:
                line_path.append(['v', [self.boxH-self.boxH/self.Htabs/4]])
            line_path.append(['h', [-self.thick]])
            
        else:
            for i in range(int(self.Htabs)):
                line_path.append(['v', [self.boxH/self.Htabs/4 + self.decalage_dimple0]])
                for l in self.thickness_line(self.dimple, 'h', -1):
                    line_path.append(l)
                line_path.append(['v', [self.boxH/self.Htabs/2 - self.decalage_dimple1 ]])
                line_path.append(['h', [self.thick]])
                line_path.append(['v', [self.boxH/self.Htabs/4 + self.decalage]])
            if not self.ht: line_path.append(['v', [self.boxH/self.Htabs/4 ]])    
            line_path.append(['h', [-self.thick]])
        # $ Bottom row of tab
        if not self.ht: line_path.append(['h', [-self.boxD/self.Dtabs/4]])
        for i in range(int(self.Dtabs)):
            line_path.append(['h', [-self.boxD/self.Dtabs/4 -self.decalage_dimple3]])#1>2
            for l in self.thickness_line(self.dimple, 'v', 1):  # this is the weird +1 instead of -1 dimple
                line_path.append(l)
            line_path.append(['h', [-self.boxD/self.Dtabs/2+self.decalage_dimple4 ]])#2>3
            line_path.append(['v', [-self.thick]])
            line_path.append(['h', [-self.boxD/self.Dtabs/4-self.decalage]])
        if not self.ht: line_path.append(['h', [-self.boxD/self.Dtabs/4]])
        line_path.append(['h', [-self.thick]])
        # $ Left
        # if fit perfectly - don't draw double line modify by Frank SAURET 12-12-2018
        if (self.kerf > 0.0 or self.forcing_separation) and (boxCover or boxSide in "Right"):
            if not self.ht: line_path.append(['v', [-self.boxH/self.Htabs/4 ]])
            for i in range(int(self.Htabs)):
                line_path.append(['v', [-self.boxH/self.Htabs/4-self.decalage]])
                line_path.append(['h', [self.thick]])
                line_path.append(['v', [-self.boxH/self.Htabs/2+self.decalage_dimple1 ]])
                for l in self.thickness_line(self.dimple, 'h', -1):
                    line_path.append(l)
                line_path.append(['v', [-self.boxH/self.Htabs/4-self.decalage_dimple0 ]])
            line_path.append(['v', [-self.pf/2 ]])    
            if not self.ht: line_path.append(['v', [-self.boxH/self.Htabs/4 ]])
        # si pas de couvercle trace une ligne sans languette
        elif boxSide in "Left" and not boxCover and (self.kerf > 0.0 or self.forcing_separation):
            line_path.append(['v', [-self.boxH]])
                
        return line_path

    ###--------------------------------------------
    ### The    main function    called    by    the    inkscape    UI
    def effect(self):
        # document dimensions (for centering)
        docW = self.svg.unittouu(self.document.getroot().get('width'))
        docH = self.svg.unittouu(self.document.getroot().get('height'))
        # extract fields from UI
        self.boxW  = self.svg.unittouu(str(self.options.width) + self.options.units)
        self.boxH  = self.svg.unittouu(str(self.options.height) + self.options.units)
        self.boxD  = self.svg.unittouu(str(self.options.depth) + self.options.units)
        self.thick = self.svg.unittouu(str(self.options.thickness) + self.options.units)
        self.kerf  = self.svg.unittouu(str(self.options.kerf_size) + self.options.units)
        #  Added by Frank SAURET 12-12-2018 
        materiaux  = self.svg.unittouu(str(self.options.materiaux) + self.options.units)
        bymaterial=self.options.bymaterial
        if bymaterial: self.kerf = materiaux
        self.aveccouvercle=self.options.aveccouvercle
        #  05-05-2021
        self.decalage = self.kerf/4 # Pour un ajustement serré si le kerf est réel
        self.decalage_dimple0 = 0 # Augmentation du jeu si utilisation de dimple
        self.decalage_dimple1 = 0 # Augmentation du jeu si utilisation de dimple
        self.decalage_dimple3 = 0 # Augmentation du jeu si utilisation de dimple
        self.decalage_dimple4 = 0 # Augmentation du jeu si utilisation de dimple        
        #  deddA by Frank SAURET 12-12-2018
        if self.kerf < 0.01: self.kerf = 0.0  # snap to 0 for UI error when setting spinner to 0.0
        self.Wtabs  = self.options.ntab_W
        self.Htabs  = self.options.ntab_H
        self.Dtabs  = self.options.ntab_D
        self.dimple = self.options.dimples
        line_width  = self.options.linewidth
        #  Added by Frank SAURET 12-12-2018
        self.forcing_separation=self.options.forcingseparation
        
        #  deddA by Frank SAURET 12-12-2018
        corners  = self.options.corners
        self.dimple_tri = self.options.dstyle
        # self.annotation = self.options.annotation
        self.ht  = self.options.halftabs
        if not self.ht:
            self.Wtabs += 0.5
            self.Htabs += 0.5
            self.Dtabs += 0.5                                

        # Correct for thickness in dimensions
        if self.options.int_ext: # external so add thickness
            self.boxW -= self.thick*2
            self.boxH -= self.thick*2
            self.boxD -= self.thick*2
        # adjust for laser kerf (precise measurement)
        self.boxW += self.kerf
        self.boxH += self.kerf
        self.boxD += self.kerf

        # Precise fit or dimples (if kerf > 0.0)
        if self.dimple == False: # and kerf > 0.0:
            self.pf = self.kerf
        else:
            self.pf = 0.0
            
        # set the stroke width and line style
        sw = self.kerf
        if self.kerf == 0.0: sw = self.stroke_width
        ls = self.line_style
        if line_width: # user wants drawn line width to be same as kerf size
            ls['stroke-width'] = sw
        line_style = str(inkex.Style(ls))

        ###--------------------------- 
        ### create the inkscape object
        box_id = self.svg.get_unique_id('box')
        self.box = g = etree.SubElement(self.svg.get_current_layer(), 'g', {'id':box_id})

        #Set local position for drawing (will transform to center of doc at end)
        lower_pos = 0
        left_pos  = 0
        # §Draw Lid (using SVG path definitions)
        line_path = self.draw_WH_lid(left_pos, lower_pos, self.aveccouvercle,'Top', False)
        # Add to scene
        line_atts = { 'style':line_style, 'id':box_id+'-lid', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # §draw the side of the box directly below modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            lower_pos += self.boxH + (3*self.thick)
        else:  # kerf = 0 so don't draw extra lines and fit perfectly
            if self.aveccouvercle:
                lower_pos += self.boxH + self.thick  # at lower edge of lid
            else:
                lower_pos += self.boxH+ self.thick *2   # at lower edge of lid
        left_pos += 0
        # Draw side of the box (placed below the lid)
        line_path = self.draw_WD_side(left_pos, lower_pos, self.aveccouvercle,'Back', False, corners=corners)
        # Add to scene
        line_atts = { 'style':line_style, 'id':box_id+'-longside1', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # §draw the bottom of the box directly below modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            lower_pos += self.boxD + (3*self.thick)
        else:  # kerf = 0 so don't draw extra lines and fit perfectly
            lower_pos += self.boxD + self.thick # at lower edge
        left_pos += 0
        # §Draw base of the box
        line_path = self.draw_WH_lid(left_pos, lower_pos, self.aveccouvercle,'Bot', True)
        # Add to scene
        line_atts = { 'style':line_style, 'id':box_id+'-base', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # draw the second side of the box directly below modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            lower_pos += self.boxH + (3*self.thick)
        else:  # kerf = 0 so don't draw extra lines and fit perfectly
            lower_pos += self.boxH + self.thick  # at lower edge of lid
        left_pos += 0
        # Draw side of the box (placed below the bottom)
        line_path = self.draw_WD_side(left_pos, lower_pos, self.aveccouvercle, 'Front', False, corners=corners)
        # Add to scene
        line_atts = { 'style':line_style, 'id':box_id+'-longside2', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # draw next on RHS of lid modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:

            left_pos += self.boxW + (2*self.thick) # adequate space (could be a param for separation when kerf > 0)
        else:
            if self.aveccouvercle:
                left_pos += self.boxW  # right at right edge of lid
            else:
                left_pos += self.boxW + (self.thick)
        lower_pos = 0
        # Side of the box (placed next to the lid)
        line_path = self.draw_HD_side(left_pos, lower_pos, self.aveccouvercle,'Left', corners, False)
        # Add to scene
        line_atts = { 'style':line_style, 'id':box_id+'-endface2', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # draw next on RHS of base modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            lower_pos += self.boxH + self.boxD + 6*self.thick
        else:
            if self.aveccouvercle:
                lower_pos += self.boxH +self.boxD + 2*self.thick
            else:
                lower_pos += self.boxH +self.boxD + 3*self.thick
                left_pos-=self.thick
        # Side of the box (placed next to the lid)
        line_path = self.draw_HD_side(left_pos, lower_pos, self.aveccouvercle,'Right', corners, True)
        # Add to scene
        line_atts = { 'style':line_style, 'id':box_id+'-endface1', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        ###----------------------------------------
        
        # Transform entire drawing to center of doc
        #lower_pos += self.boxH*2 + self.boxD*2 + 2*self.thick
        #left_pos += self.boxH + 2*self.thick
        #g.set( 'transform', 'translate(%f,%f)' % ( (docW-left_pos)/2, (docH-lower_pos)/2))
        # Transform entire drawing to uper left corner + 10 mm
        g.set( 'transform', 'translate(%f,%f)' % ( self.thick+self.kerf/2+10,self.thick+self.kerf/2+10))

###
if __name__ == '__main__':
    e = LasercutBox()
    e.run()