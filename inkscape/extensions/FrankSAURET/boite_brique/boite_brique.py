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
# - If zero kerf it will be perfectly packed for minimal laser cuts and material size.

### Tàf
#  Ajouter une fonction pour faire un couvercle mobile et son reposoir

### Versions
# 2026.1 Ajout de Info.json pour compatibilité abec Màj
# 2024.1 Ajout d'un paramètre permettant de changer l'espacement des pièces
#        Suppression des bosses (dimple),
#        Suppression du dessin sans encoche de demi taille prés des coins,
#        Ajustement du dessin pour respecter le trait de coupe.
#        Changement de versionnage.
#  0.6  Suppression des unittoouu, 
#       Renommage des variables et rationalisation des commentaires,
#       Changement des couleurs,
#       Changement du versionning.
#  0.5 Modify tab for adjust kerf (increase tab size)
#  0.4 Add option for lid or not
# [Frank SAURET - ^^^^ depuis 2018 ^^^^]
#  0.3 Option to avoid half-sized tabs at corners. <juergen@fabmail.org>
#  0.2 changes to unittouu for Inkscape 0.91
#  0.1 February 2011 - basic lasercut box with dimples etc


# Charger la version depuis Info.json
import json
import os
INFO_PATH = os.path.join(os.path.dirname(__file__), 'Info.json')
with open(INFO_PATH, encoding='utf-8') as f:
    __version__ = json.load(f)["version"]

#from math import *
import sys
import inkex
from simplepath import *
from lxml import etree

class LasercutBox(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)
        # * Onglet "Dimensions"
        self.arg_parser.add_argument("-C", "--aveccouvercle",
                type=inkex.Boolean,
                dest="aveccouvercle", default=True,
                help="Box is closed or not")
        self.arg_parser.add_argument("-i", "--external_dimensions",
                        type=inkex.Boolean,
                        dest="external_dimensions", default=False,
                        help="Are the Dimensions for External (True) or Internal (False) sizing.")
        self.arg_parser.add_argument("-u", "--units",
                        type=str,
                        dest="units", default="mm",
                        help="The unit of the box dimensions")        
        self.arg_parser.add_argument("-x", "--width",
                        type=float,
                        dest="width", default=30.0,
                        help="The Box Width - in the X dimension")
        self.arg_parser.add_argument("-y", "--length",
                        type=float,
                        dest="length", default=60.0,
                        help="The Box length - in the Y dimension")
        self.arg_parser.add_argument("-z", "--height",
                        type=float,
                        dest="height", default=30.0,
                        help="The Box height - in the Z dimension")
        self.arg_parser.add_argument("-t", "--thickness",
                        type=float,
                        dest="thickness", default=3.0,
                        help="Material Thickness")
        self.arg_parser.add_argument("-p", "--num_tab_Width",
                        type=int,
                        dest="num_tab_Width", default=3,
                        help="Number of tabs in Width")        
        self.arg_parser.add_argument("-q", "--num_tab_Length",
                        type=int,
                        dest="num_tab_Length", default=3,
                        help="Number of tabs in length")        
        self.arg_parser.add_argument("-r", "--num_tab_Height",
                        type=int,
                        dest="num_tab_Height", default=3,
                        help="Number of tabs in height")
        self.arg_parser.add_argument("-c", "--corners",
                        type=inkex.Boolean,
                        dest="corners", default=True,
                        help="The corner cubes can be removed for a different look")
        self.arg_parser.add_argument("-dbs", "--distance_between_side",
                        type=float,
                        dest="distance_between_side", default=2.0,
                        help="Distance between side")        
        # * Onglet "trait de coupe"
        self.arg_parser.add_argument("-b", "--bymaterial",
                        type=inkex.Boolean,
                        dest="bymaterial", default=True,
                        help="Are kerf define by material")
        self.arg_parser.add_argument("-o", "--materiaux",
                        type=float,
                        dest="materiaux", default=0.15,
                        help="Kerf size define by material")
        self.arg_parser.add_argument("-k", "--kerf_size",
                        type=float,
                        dest="kerf_size", default=0.0,
                        help="Kerf size - amount lost to laser for this material. 0 = loose fit")
        self.arg_parser.add_argument("-g", "--linewidth",
                        type=inkex.Boolean,
                        dest="linewidth", default=True,
                        help="Use the kerf value as the drawn line width")        
        self.arg_parser.add_argument("-f", "--forcingseparation",
                        type=inkex.Boolean,
                        dest="forcingseparation", default=False,
                        help="Forcing the separation of the panels")
        # * L'onglet séléectionné
        self.arg_parser.add_argument("--tab",
                        type=str, 
                        dest="tab", 
                        default="use",
                        help="The selected UI-tab when OK was pressed")
        #internal useful variables
        self.stroke_width  = 0.1 #default for visibility
        self.external_line_style = {'stroke':          '#660066', # Violet
                           'fill':            'none',
                           'stroke-width':    self.stroke_width,
                           'stroke-linecap':  'butt',
                           'stroke-linejoin': 'miter'}
        self.internal_line_style = {'stroke':          '#006633', # Vert foncé
                           'fill':            'none',
                           'stroke-width':    self.stroke_width,
                           'stroke-linecap':  'butt',
                           'stroke-linejoin': 'miter'}
    
    def draw_top_bottom(self, startx, starty, boxCover, boxSide, masktop=False):
        """ Return an SVG path for the top or bottom of box
        """
        line_path = []
        line_path.append(['M', [startx, starty]])
        
        # * Trace le dessus de la boite sans languettes
        if boxSide in "Top" and not boxCover:
            line_path.append(['m', [-self.materialThickness, -self.materialThickness]])
            line_path.append(['h', [self.boxWidth+self.materialThickness*2]])
            line_path.append(['v', [self.boxLength+self.materialThickness*2]])
            line_path.append(['h', [-self.boxWidth-self.materialThickness*2]])
            line_path.append(['v', [-self.boxLength-self.materialThickness*2-self.kerf/2]])
        else:
            # $ top row of tabs 
            if masktop and self.kerf ==0.0 and not self.forcing_separation: # don't draw top for packing with no extra cuts
                line_path.append(['m', [self.boxWidth,0]])
            else:
                for i in range(int(self.num_tab_W)):
                    line_path.append(['h', [self.boxWidth/self.num_tab_W/4-self.kerf/2]])
                    line_path.append(['v', [-self.materialThickness]])
                    line_path.append(['h', [self.boxWidth/self.num_tab_W/2+self.kerf]])
                    line_path.append(['v', [self.materialThickness]])
                    line_path.append(['h', [self.boxWidth/self.num_tab_W/4-self.kerf/2]])
            # $ right hand vertical drop
            for i in range(int(self.num_tab_L)):
                line_path.append(['v', [self.boxLength/self.num_tab_L/4 - self.kerf/2]])
                line_path.append(['h', [self.materialThickness]])
                line_path.append(['v', [self.boxLength/self.num_tab_L/2 + self.kerf]])
                line_path.append(['h', [-self.materialThickness]])
                line_path.append(['v', [self.boxLength/self.num_tab_L/4 - self.kerf/2]])
            # $ bottom row (in reverse)
            for i in range(int(self.num_tab_W)):
                line_path.append(['h', [-self.boxWidth/self.num_tab_W/4+self.kerf/2 ]])
                line_path.append(['v', [self.materialThickness]])
                line_path.append(['h', [-self.boxWidth/self.num_tab_W/2 -self.kerf]])
                line_path.append(['v', [-self.materialThickness]])
                line_path.append(['h', [-self.boxWidth/self.num_tab_W/4+self.kerf/2]])
            # $ up the left hand side
            for i in range(int(self.num_tab_L)):
                line_path.append(['v', [-self.boxLength/self.num_tab_L/4 +self.kerf/2]])
                line_path.append(['h', [-self.materialThickness]])
                line_path.append(['v', [-self.boxLength/self.num_tab_L/2 -self.kerf]])
                line_path.append(['h', [self.materialThickness]])
                line_path.append(['v', [-self.boxLength/self.num_tab_L/4+self.kerf/2 ]])
            line_path.append(['v', [-self.kerf/2 ]])    
        return line_path

    def draw_short_side(self, startx, starty, boxCover, boxSide, corners=True):
        """ Return an SVG path for the short side of box
        """
        # Draw side of the box (placed below the lid)
        line_path = []
        # $ top row of tabs
        if corners:
            line_path.append(['M', [startx - self.materialThickness, starty]])
            line_path.append(['v', [-self.materialThickness]])
            line_path.append(['h', [self.materialThickness]])
        else:
            line_path.append(['M', [startx, starty]])
            line_path.append(['v', [-self.materialThickness]])
        #
        # if fit perfectly - don't draw double line  modify by Frank SAURET 12-12-2018
        if boxSide in "Back" and not boxCover:
            if self.kerf == 0.0 and not self.forcing_separation:
                if corners:
                    line_path.append(['m', [self.boxWidth+self.materialThickness,0]])
                else:
                    line_path.append(['m', [self.boxWidth,0]])
            else:       
                if corners:
                    line_path.append(['h', [self.boxWidth+self.materialThickness]])
                else:
                    line_path.append(['h', [self.boxWidth]])
        else:
            if self.kerf > 0.0 or self.forcing_separation:
                for i in range(int(self.num_tab_W)):
                    line_path.append(['h', [self.boxWidth/self.num_tab_W/4 + self.kerf/2]])
                    line_path.append(['v', [self.materialThickness]])
                    line_path.append(['h', [self.boxWidth/self.num_tab_W/2 - self.kerf]])
                    line_path.append(['v', [-self.materialThickness]])
                    line_path.append(['h', [self.boxWidth/self.num_tab_W/4 + self.kerf/2 ]])
                if corners: line_path.append(['h', [self.materialThickness]])
            else: # move to skipped drawn lines
                if corners:    
                    line_path.append(['m', [self.boxWidth + self.materialThickness, 0]])
                else:
                    line_path.append(['m', [self.boxWidth, 0]])
        #
        line_path.append(['v', [self.materialThickness]])
        if not corners: 
            line_path.append(['h', [self.materialThickness]])
        # $ Right hand side
        for i in range(int(self.num_tab_H)):
            line_path.append(['v', [self.boxHeight/self.num_tab_H/4 + self.kerf/2]])
            line_path.append(['h', [-self.materialThickness]])
            line_path.append(['v', [self.boxHeight/self.num_tab_H/2 - self.kerf ]])
            line_path.append(['h', [self.materialThickness]])
            line_path.append(['v', [self.boxHeight/self.num_tab_H/4 + self.kerf/2]])
        #
        if corners:
            line_path.append(['v', [self.materialThickness]])
            line_path.append(['h', [-self.materialThickness]])
        else:
            line_path.append(['h', [-self.materialThickness]])
            line_path.append(['v', [self.materialThickness]])
        # $ Bottom row of tabs
        if boxSide in "Front" and not boxCover:
            if corners:
                line_path.append(['h', [-self.boxWidth]])
            else:
                line_path.append(['h', [-self.boxWidth]])
        else:
            for i in range(int(self.num_tab_W)):
                line_path.append(['h', [-self.boxWidth/self.num_tab_W/4 -self.kerf/2]])
                line_path.append(['v', [-self.materialThickness]])
                line_path.append(['h', [-self.boxWidth/self.num_tab_W/2+self.kerf]])
                line_path.append(['v', [self.materialThickness]])
                line_path.append(['h', [-self.boxWidth/self.num_tab_W/4-self.kerf/2]]) 
        #
        if corners:
            line_path.append(['h', [-self.materialThickness]])
            line_path.append(['v', [-self.materialThickness]])
        else:
            line_path.append(['v', [-self.materialThickness]])
            line_path.append(['h', [-self.materialThickness]])
        # $ Left hand side
        for i in range(int(self.num_tab_H)):
            line_path.append(['v', [-self.boxHeight/self.num_tab_H/4 -self.kerf/2]])
            line_path.append(['h', [self.materialThickness]])
            line_path.append(['v', [-self.boxHeight/self.num_tab_H/2+self.kerf]])
            line_path.append(['h', [-self.materialThickness]])
            line_path.append(['v', [-self.boxHeight/self.num_tab_H/4-self.kerf/2]])
        #
        line_path.append(['h', [self.kerf/2 ]])
        if not corners: 
            line_path.append(['h', [self.materialThickness]])
        return line_path

    def draw_long_side(self, startx, starty, boxCover, boxSide, corners):
        """ Return an SVG path for the long side of box
        """
        line_path = []
        # $ top row of tabs
        line_path.append(['M', [startx, starty]])
        line_path.append(['h', [self.materialThickness]])
        for i in range(int(self.num_tab_H)):
            line_path.append(['h', [self.boxHeight/self.num_tab_H/4-self.kerf/2]])
            line_path.append(['v', [-self.materialThickness]])
            line_path.append(['h', [self.boxHeight/self.num_tab_H/2+self.kerf]]) 
            line_path.append(['v', [self.materialThickness]])
            line_path.append(['h', [self.boxHeight/self.num_tab_H/4 -self.kerf/2]])
        line_path.append(['h', [self.materialThickness]])
        # $ Right row of tabs or line
        if boxSide in "Right" and not boxCover:
            line_path.append(['v', [self.boxLength]])
            line_path.append(['h', [-self.materialThickness]])
        else:
            for i in range(int(self.num_tab_L)):
                line_path.append(['v', [self.boxLength/self.num_tab_L/4 + self.kerf/2]])
                line_path.append(['h', [-self.materialThickness]])
                line_path.append(['v', [self.boxLength/self.num_tab_L/2 - self.kerf]])
                line_path.append(['h', [self.materialThickness]])
                line_path.append(['v', [self.boxLength/self.num_tab_L/4 + self.kerf/2]])
            line_path.append(['h', [-self.materialThickness]])
        # $ Bottom row of tab
        for i in range(int(self.num_tab_H)):
            line_path.append(['h', [-self.boxHeight/self.num_tab_H/4 -self.kerf/2]])
            line_path.append(['v', [self.materialThickness]])
            line_path.append(['h', [-self.boxHeight/self.num_tab_H/2+self.kerf ]])#2>3
            line_path.append(['v', [-self.materialThickness]])
            line_path.append(['h', [-self.boxHeight/self.num_tab_H/4-self.kerf/2]])
        line_path.append(['h', [-self.materialThickness]])
        # $ Left hand
        # if fit perfectly - don't draw double line modify by Frank SAURET 12-12-2018
        if (self.kerf > 0.0 or self.forcing_separation) and (boxCover or boxSide in "Right"):
            for i in range(int(self.num_tab_L)):
                line_path.append(['v', [-self.boxLength/self.num_tab_L/4-self.kerf/2]])
                line_path.append(['h', [self.materialThickness]])
                line_path.append(['v', [-self.boxLength/self.num_tab_L/2+self.kerf]]) 
                line_path.append(['h', [-self.materialThickness]])
                line_path.append(['v', [-self.boxLength/self.num_tab_L/4-self.kerf/2]])
            line_path.append(['v', [-self.kerf/2 ]])    
        # si pas de couvercle trace une ligne sans languette
        elif boxSide in "Left" and not boxCover and (self.kerf > 0.0 or self.forcing_separation):
            line_path.append(['v', [-self.boxLength-self.kerf/2]])
                
        return line_path

    # 1- The main function called by the inkscape UI ***************************************************
    def effect(self):
        # 2- extract fields from UI ***************************************************
        self.boxWidth  = self.options.width
        self.boxLength  = self.options.length
        self.boxHeight  = self.options.height
        self.materialThickness = self.options.thickness
        self.kerf  = self.options.kerf_size
        materiaux  = self.options.materiaux
        bymaterial=self.options.bymaterial
        if bymaterial: 
            self.kerf = materiaux
        self.aveccouvercle=self.options.aveccouvercle
        self.num_tab_W  = self.options.num_tab_Width
        self.num_tab_L  = self.options.num_tab_Length
        self.num_tab_H  = self.options.num_tab_Height
        self.forcing_separation=self.options.forcingseparation
        corners  = self.options.corners
        # 3- Correct for thickness in dimensions
        if self.options.external_dimensions: # external donc enlève l'épaisseur
            self.boxWidth -= self.materialThickness*2
            self.boxLength -= self.materialThickness*2
            self.boxHeight -= self.materialThickness*2
        # 3- adjust for laser kerf (precise measurement)
        self.boxWidth += self.kerf
        self.boxLength += self.kerf
        self.boxHeight += self.kerf
        # 3- set the stroke width and line style
        ls = self.external_line_style
        if self.kerf == 0.0:
            ls['stroke-width'] =self.stroke_width
        else:
            ls['stroke-width'] = self.kerf    
        external_line_style = str(inkex.Style(ls))

        # 2- create the inkscape object ***************************************************
        box_id = self.svg.get_unique_id('box')
        self.box = g = etree.SubElement(self.svg.get_current_layer(), 'g', {'id':box_id})

        # 3- Set local position for drawing the box
        y_pos = 0
        x_pos  = 0
        # §Draw top (using SVG path definitions)
        line_path = self.draw_top_bottom(x_pos, y_pos, self.aveccouvercle,'Top', False)
        # 3- Add to scene
        line_atts = { 'style':external_line_style, 'id':box_id+'-lid', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # §draw the short side 1 of the box directly below modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            y_pos += self.boxLength + 2*self.materialThickness+self.options.distance_between_side
        else:  # kerf = 0 so don't draw extra lines and fit perfectly
            if self.aveccouvercle:
                y_pos += self.boxLength + self.materialThickness  # at lower edge of lid
            else:
                y_pos += self.boxLength+ self.materialThickness *2   # at lower edge of lid
        x_pos += 0
        # 3- Draw side of the box (placed below the top)
        line_path = self.draw_short_side(x_pos, y_pos, self.aveccouvercle,'Back', corners=corners)
        # 3- Add to scene
        line_atts = { 'style':external_line_style, 'id':box_id+'-longside1', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # §draw the bottom of the box directly below modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            y_pos += self.boxHeight + 2*self.materialThickness+self.options.distance_between_side
        else:  # kerf = 0 so don't draw extra lines and fit perfectly
            y_pos += self.boxHeight + self.materialThickness # at lower edge
        x_pos += 0
        line_path = self.draw_top_bottom(x_pos, y_pos, self.aveccouvercle,'Bot', True)
        # 3- Add to scene
        line_atts = { 'style':external_line_style, 'id':box_id+'-base', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # §  draw the second short side 2 of the box directly below modify by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            y_pos += self.boxLength + 2*self.materialThickness+self.options.distance_between_side
        else:  # kerf = 0 so don't draw extra lines and fit perfectly
            y_pos += self.boxLength + self.materialThickness  # at lower edge of lid
        x_pos += 0
        # 3- Draw side of the box (placed below the bottom)
        line_path = self.draw_short_side(x_pos, y_pos, self.aveccouvercle, 'Front', corners=corners)
        # 3- Add to scene
        line_atts = { 'style':external_line_style, 'id':box_id+'-longside2', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # § draw long side 1 next to top by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            x_pos += self.boxWidth + self.materialThickness + self.options.distance_between_side
        else:
            if self.aveccouvercle:
                x_pos += self.boxWidth  # right at right edge of lid
            else:
                x_pos += self.boxWidth + (self.materialThickness)
        y_pos = 0
        # 3- Side of the box (placed next to the top)
        line_path = self.draw_long_side(x_pos, y_pos, self.aveccouvercle,'Left', corners)
        # 3- Add to scene
        line_atts = { 'style':external_line_style, 'id':box_id+'-endface2', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # § draw long side 2 next to bottom by Frank SAURET 12-12-2018
        if self.kerf > 0.0 or self.forcing_separation:
            y_pos += self.boxLength + 2*self.materialThickness + self.options.distance_between_side
        else:
            if self.aveccouvercle:
                y_pos += self.boxLength +self.boxHeight + 2*self.materialThickness
            else:
                y_pos += self.boxLength +self.boxHeight + 3*self.materialThickness
                x_pos-=self.materialThickness
        # 3- Side of the box (placed next to the lid)
        line_path = self.draw_long_side(x_pos, y_pos, self.aveccouvercle,'Right', corners)
        # 3- Add to scene
        line_atts = { 'style':external_line_style, 'id':box_id+'-endface1', 'd':str(Path(line_path)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts)

        # § Transform entire drawing to center view
        bbox = g.bounding_box()
        bbox_width = bbox.width
        bbox_height = bbox.height
        translate_x = self.svg.namedview.center[0] - bbox_width / 2
        translate_y = self.svg.namedview.center[1] - bbox_height / 2
        g.set('transform', 'translate(%f,%f)' % (translate_x, translate_y))

###
if __name__ == '__main__':
    LasercutBox().run()
    
#Pour débugger dans VSCode et en lançant InkScape    
# if __name__ == '__main__':
#     filename='H:\\OneDrive\\TestBoiteBrique.svg'
#     if 'inkscape' in sys.argv[0]:
#         # Dans VSCode
#         input_file = filename
#         output_file = input_file
#         LasercutBox().run([input_file, '--output=' + output_file])
#     else:
#         LasercutBox().run()