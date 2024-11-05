#!/usr/bin/env python
'''
Copyright (C) 2017 Jarrett Rainier jrainier@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

tàf : Permettre la sélection multiple de bords pour appliquer en une fois.
 
2024.2 : 
- Réorganisation onglet et suppression des messages de debogage
- Conversion automatique des formes en chemins

2021 :
- Added option bymaterial to change kerf
- Reorganise app tab to add function "tab, slot and both (to draw tab and slot)".

'''
__version__ = "2024.2"

import inkex, cmath
from inkex.paths import Path, ZoneClose, Move
from lxml import etree
    
   
def linesNumber(path):
    retval = -1
    for elem in path:
        retval = retval + 1
    return retval

def to_complex(point):
    if "C" in str(point): 
        point.x=point.x4
        point.y=point.y4
    return (round(point.x,2)+ round(point.y,2)*1j)

class QuickJoint(inkex.Effect):
    def add_arguments(self, pars):
        # § Onglet Languette - Fente
        pars.add_argument('--side', 
                        type=int, 
                        default=0, 
                        help='Object face to tabify')
        pars.add_argument('--numtabs', 
                        type=int, 
                        default=1, 
                        help='Number of tabs to add')
        pars.add_argument("--typedeliaison", 
                        type=str, 
                        default="LesDeux", 
                        help='Languette, fente ou les deux.')
        pars.add_argument("--gardejeu", 
                        type=inkex.Boolean, 
                        default=False, 
                        help="keep space") 
        # § Onglet Trait de coupe
        pars.add_argument("--bymaterial", 
                        type=inkex.Boolean, 
                        default=False, 
                        help="Are kerf define by material")
        pars.add_argument("--materiaux", 
                        type=float, 
                        default=0.0, 
                        help="Kerf size define by material")
        pars.add_argument('--kerf', 
                        type=float, 
                        default=0.14, 
                        help='Measured kerf of cutter')
        # § Fenètre principale        
        pars.add_argument('--thickness', 
                        type=float, 
                        default=3.0, 
                        help='Material thickness')
        pars.add_argument('--units', 
                        type=str,
                        default='mm', 
                        help='Measurement units')
        pars.add_argument('--edgefeatures', 
                        type=inkex.Boolean, 
                        default=False, 
                        help='Allow tabs to go right to edges')
        pars.add_argument('--flipside',
                        type=inkex.Boolean, 
                        default=False, 
                        help='Flip side of lines that tabs are drawn onto')
        pars.add_argument('--activetab', 
                        default='', 
                        help='Tab or slot menus')

    def get_length(self, line):
        polR, polPhi = cmath.polar(line)
        return polR
        
    def draw_parallel(self, start, guideLine, stepDistance):
        polR, polPhi = cmath.polar(guideLine)
        polR = stepDistance
        TempComplexe=cmath.rect(polR, polPhi) + start
        TempComplexe=round(TempComplexe.real,2)+round(TempComplexe.imag,2)*1j
        return (TempComplexe)
        
    def draw_perpendicular(self, start, guideLine, stepDistance, invert = False):
        polR, polPhi = cmath.polar(guideLine)
        polR = stepDistance
        if invert:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        TempComplexe=cmath.rect(polR, polPhi) + start
        TempComplexe=round(TempComplexe.real,2)+round(TempComplexe.imag,2)*1j
        return (TempComplexe)
        
    def draw_box(self, start, guideLine, xDistance, yDistance, kerf, jeu):
        polR, polPhi = cmath.polar(guideLine)
        
        #Kerf expansion
        if self.flipside:  
            start += cmath.rect(kerf , polPhi)
            start += cmath.rect(kerf , polPhi + (cmath.pi / 2))
        else:
            start += cmath.rect(kerf , polPhi)
            start += cmath.rect(kerf , polPhi - (cmath.pi / 2))
            
        lines = []
        lines.append(['M', [start.real, start.imag]])
        
        #Horizontal
        polR = xDistance
        move = cmath.rect(polR - 2*kerf, polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        #Vertical
        polR = yDistance
        if self.flipside:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        move = cmath.rect(polR  - jeu, polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        #Horizontal
        polR = xDistance
        if self.flipside:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        move = cmath.rect(polR - 2*kerf, polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        lines.append(['Z', []])
        
        return lines
    
    def draw_tabs(self, path, line):
        #Male tab creation
        start = to_complex(path[line])

        closePath = False
        #Line is between last and first (closed) nodes
        end = None
        if isinstance(path[line+1], ZoneClose):
            end = to_complex(path[0])
            closePath = True
        else:
            end = to_complex(path[line+1])

        if self.edgefeatures:
            segCount = (self.numtabs * 2) - 1
            drawValley = False
        else:
            segCount = (self.numtabs * 2)
            drawValley = False
          
        distance = end - start
        
        try:
            if self.edgefeatures:
                segLength = self.get_length(distance) / segCount
            else:
                segLength = self.get_length(distance) / (segCount + 1)
        except:
            segLength = self.get_length(distance)
        
        newLines = []
        
        # when handling first line need to set M back
        if isinstance(path[line], Move):
            newLines.append(['M', [start.real, start.imag]])

        if self.edgefeatures == False:
            newLines.append(['L', [start.real, start.imag]])
            start = self.draw_parallel(start, distance, segLength)
            newLines.append(['L', [start.real, start.imag]])
            
        for i in range(segCount):
            if drawValley == True:
                #Vertical
                start = self.draw_perpendicular(start, distance, self.thickness, self.flipside)
                newLines.append(['L', [start.real, start.imag]])
                drawValley = False
                #Horizontal
                start = self.draw_parallel(start, distance, segLength)
                newLines.append(['L', [start.real, start.imag]])
            else:
                #Vertical
                start = self.draw_perpendicular(start, distance, self.thickness, not self.flipside)
                newLines.append(['L', [start.real, start.imag]])
                drawValley = True
                #Horizontal
                start = self.draw_parallel(start, distance, segLength)
                newLines.append(['L', [start.real, start.imag]])
                
        if self.edgefeatures == True:
            start = self.draw_perpendicular(start, distance, self.thickness, self.flipside)
            newLines.append(['L', [start.real, start.imag]])
            
        if closePath:
            newLines.append(['Z', []])
        return newLines
        
    def draw_slots(self, path, line):
        #Female slot creation
        start = to_complex(path[line])
  
        #Line is between last and first (closed) nodes
        end = None
        if isinstance(path[line+1], ZoneClose):
            end = to_complex(path[0])
        else:
            end = to_complex(path[line+1])

        if not self.flipside:
            if self.edgefeatures:
                self.numslots-=1 
            else:
                self.numslots+=1
        
        if self.edgefeatures:
            segCount = (self.numslots * 2) - 1 
        else:
            segCount = (self.numslots * 2)

        distance = end - start
        
        try:
            if self.edgefeatures:
                segLength = self.get_length(distance) / segCount
            else:
                segLength = self.get_length(distance) / (segCount + 1)
        except:
            segLength = self.get_length(distance)

        newLines = []
        
        line_style = str(inkex.Style({ 'stroke': '#FF0000', 'fill': 'none', 'stroke-width': str(self.kerf) }))

        slot_id = self.svg.get_unique_id('slot')
        g = etree.SubElement(self.svg.get_current_layer(), 'g', {'id':slot_id})        
        for i in range(segCount):
            if (self.edgefeatures and (i % 2) == 0) or (not self.edgefeatures and (i % 2)):
                newLines = self.draw_box(start, distance, segLength, self.thickness, self.kerf, self.jeu)
                
                line_atts = { 'style':line_style, 'id':slot_id+str(i)+'-inner-close-tab', 'd':str(Path(newLines)) }
                etree.SubElement(g, inkex.addNS('path','svg'), line_atts )
                
            #Find next point
            polR, polPhi = cmath.polar(distance)
            polR = segLength
            start = cmath.rect(polR, polPhi) + start
    
    def convert_to_path(self, elem):
        # Fonction pour convertir un élément en chemin
        d = elem.path.to_arrays()
        path = inkex.PathElement()
        path.path = d
        path.style = elem.style
        return path
        
    def effect(self):
        # 1- Récupération des paramètres
        self.side  = self.options.side
        self.numtabs  = self.options.numtabs
        self.numslots  = self.options.numtabs
        self.thickness = self.svg.unittouu(str(self.options.thickness) + self.options.units)
        self.kerf = self.svg.unittouu(str(self.options.kerf) + self.options.units)
        self.units = self.options.units
        self.edgefeatures = self.options.edgefeatures
        self.flipside = self.options.flipside
       
        materiaux  = self.svg.unittouu(str(self.options.materiaux) + self.options.units)
        bymaterial=self.options.bymaterial
        if bymaterial: self.kerf = materiaux
        self.typedeliaison=self.options.typedeliaison
        if self.options.gardejeu:
            self.jeu=0
        else:
            self.jeu=self.kerf    
        
        # 1- Convertir les formes sélectionnées en chemins
        for elem in self.svg.selected.values():
            if elem.tag in [inkex.addNS('rect', 'svg'), inkex.addNS('circle', 'svg'), inkex.addNS('ellipse', 'svg'), inkex.addNS('line', 'svg'), inkex.addNS('polyline', 'svg'), inkex.addNS('polygon', 'svg')]:
                path = self.convert_to_path(elem)
                self.svg.selected.add(path)
                self.svg.selected.pop(elem)
                elem.getparent().replace(elem, path)

        # 1- Traitement des objets sélectionnés
        for id, node in self.svg.selected.items():
            
            if node.tag == inkex.addNS('path','svg'):

                p = list(node.path.to_superpath().to_segments())

                # Suppression des points doublés
                i = 0
                while i < len(p)-1:
                    if p[i] == p[i+1]:
                        del p[i]
                    else:
                        i = i+1
                # Suppression du dernier point si identique au premier     

                if "l" in str(p[i-1]).lower():
                    if p[0].x==p[i-1].x and p[0].y==p[i-1].y : 
                        del p[i-1]

                lines = linesNumber(p)
                lineNum = self.side % lines
                # £ Ignorer les curves

                while "c" in str(p[lineNum]).lower(): 
                    lineNum+=1
                
                newPath = []
                if self.typedeliaison == 'Languette':
                    newPath = self.draw_tabs(p, lineNum)
                    finalPath = p[:lineNum] + newPath + p[lineNum + 1:]
                    node.set('d',str(Path(finalPath)))
                elif self.typedeliaison == 'Fente':
                    newPath = self.draw_slots(p, lineNum)
                else:
                    newPath = self.draw_tabs(p, lineNum)

                    finalPath = p[:lineNum] + newPath + p[lineNum + 1:]
                    node.set('d',str(Path(finalPath)))
                    newPath = self.draw_slots(p, lineNum)




if __name__ == '__main__':
    QuickJoint().run()
