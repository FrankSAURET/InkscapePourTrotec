#!/usr/bin/env python3
'''
Copyright (C) 2007 Aaron Spike  (aaron @ ekips.org)
Copyright (C) 2007 Tavmjong Bah (tavmjong @ free.fr)
Copyright (C) http://cnc-club.ru/forum/viewtopic.php?f=33&t=434&p=2594#p2500
Copyright (C) 2014 Jürgen Weigert (juewei@fabmail.org)
Copyright (C) 2020 Spadino (spada.andrea @ gmail DOT com)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

2014-03-20 jw@suse.de 0.2  Option --accuracy=0 for automatic added.
2014-03-21                 sent upstream: https://bugs.launchpad.net/inkscape/+bug/1295641
2014-03-21 jw@suse.de 0.3  Fixed center of rotation for gears with odd number of teeth.
2014-04-04 juewei     0.7  Revamped calc_unit_factor(). 
2014-04-05 juewei    0.7a  Correctly positioned rack gear.
                       The geometry above the meshing line is wrong.
2014-04-06 juewei    0.7b  Undercut detection added. Reference:
               http://nptel.ac.in/courses/IIT-MADRAS/Machine_Design_II/pdf/2_2.pdf
               Manually merged https://github.com/jnweiger/inkscape-gears-dev/pull/15
2014-04-07 juewei    0.7c  Manually merged https://github.com/jnweiger/inkscape-gears-dev/pull/17
2014-04-09 juewei    0.8   Fixed https://github.com/jnweiger/inkscape-gears-dev/issues/19
			   Ring gears are ready for production now. Thanks neon22 for driving this.
			   Profile shift implemented (Advanced Tab), fixing 
			   https://github.com/jnweiger/inkscape-gears-dev/issues/9
2015-05-29 juewei 0.9 	ported to inkscape 0.91
			AttributeError: 'module' object inkex has no attribute 'uutounit
			Fixed https://github.com/jnweiger/inkscape-gears-dev
2020-7-4   spadino 1.0 ported to inkscape 1.0
2024-04-21 Frank sauret 1.1 : traduction en français. Modification de la couleur en cas d'undercut. Modification du deddendum pour qu'il fasse 1.25 fois l'addendum.
2024-06-18 Frank sauret 1.2 : Ajout de la possibilité de choisir la forme du trou (rectangulaire, ronde ou empreinte de servo) et de choisir les dimensions du trou. Ajout de la possibilité de choisir une empreinte pour le trou du servo. Les empreintes sont placées dans le fichier engrenage.ini
2024-06-22 Frank sauret 1.3 : Ajout de couleurs pour l'ordre de découpe. Séparation en plusieurs objet pour faciliter la retouche et la recolorisation.
2024-07-20 Frank sauret 1.4 : Ajout du tracé de poulie au pas métrique
2024-10-25 Frank sauret 2024.1 : Ajout du tracé de roue de fixation pour les servomoteurs. Changement de versionnage
2024-11-06 Frank sauret 2024.2 : La roue de fixation pour les servomoteurs est maintenant paramétrable. 
'''

import inkex
from lxml import etree
from math import pi, cos, sin, tan, radians, degrees, ceil, asin, acos, sqrt, hypot
from configparser import ConfigParser
import numpy as np
two_pi = 2 * np.pi
import locale
locale.setlocale(locale.LC_ALL, '')

__version__ = '2024.2'

def uutounit(self,nn,uu):
    return self.svg.uutounit(nn,uu)

def linspace(a,b,n):
    """ return list of linear interp of a to b in n steps
        - if a and b are ints - you'll get an int result.
        - n must be an integer
    """
    return [a+x*(b-a)/(n-1) for x in range(0,n)]

def involute_intersect_angle(Rb, R):
    """_summary_

    Args:
        Rb (_type_): _description_
        R (_type_): _description_

    Returns:
        _type_: _description_
    """
    " "
    Rb, R = float(Rb), float(R)
    return (sqrt(R**2 - Rb**2) / (Rb)) - (acos(Rb / R))

def point_on_circle(radius, angle):
    """Calcule les coordonnées d'un point sur un cercle. données un rayon et un angle.
    Args:
        radius (float): rayon du cercle
        angle (float): angle en radians entre 2 points 
    Returns:
        point (tupple): x, y 
    """
    x = radius * np.cos(angle)
    y = radius * np.sin(angle)
    return (x, y)
    
def points_to_bbox(p):
    """ from a list of points (x,y pairs)
        - return the lower-left xy and upper-right xy
    """
    llx = urx = p[0][0]
    lly = ury = p[0][1]
    for x in p[1:]:
        if   x[0] < llx: llx = x[0]
        elif x[0] > urx: urx = x[0]
        if   x[1] < lly: lly = x[1]
        elif x[1] > ury: ury = x[1]
    return (llx, lly, urx, ury)

def points_to_bbox_center(p):
    """ from a list of points (x,y pairs)
        - find midpoint of bounding box around all points
        - return (x,y)
    """
    bbox = points_to_bbox(p)
    return ((bbox[0]+bbox[2])/2.0, (bbox[1]+bbox[3])/2.0)

def points_to_svgd(p):
    " convert list of points into a closed SVG path list"
    f = p[0]
    p = p[1:]
    svgd = 'M%.4f,%.4f' % f
    for x in p:
        svgd += 'L%.4f,%.4f' % x
    svgd += 'z'
    return svgd

def draw_SVG_circle(parent, r, cx, cy, name, style):
    " add an SVG circle entity to parent "
    circ_attribs = {'style': str(inkex.Style(style)),
                    'cx': str(cx), 'cy': str(cy), 
                    'r': str(r),
                    inkex.addNS('label','inkscape'):name}
    circle = etree.SubElement(parent, inkex.addNS('circle','svg'), circ_attribs )

def draw_SVG_rect(parent, x, y, w, h, name, style):
    " add an SVG rectangle entity to parent "
    rect_attribs = {'style': str(inkex.Style(style)),
                    'x': str(x), 'y': str(y), 
                    'width': str(w), 'height': str(h),
                    inkex.addNS('label','inkscape'):name}
    rect = etree.SubElement(parent, inkex.addNS('rect','svg'), rect_attribs )

### Undercut support functions
def undercut_min_teeth(pitch_angle, k=1.0):
    """ computes the minimum tooth count for a 
        spur gear so that no undercut with the given pitch_angle (in deg) 
        and an addendum = k * metric_module, where 0 < k < 1
    Note:
    The return value should be rounded upwards for perfect safety. E.g.
    min_teeth = int(math.ceil(undercut_min_teeth(20.0)))    # 18, not 17
    """
    x = sin(radians(pitch_angle))
    return 2*k /(x*x)

def undercut_max_k(teeth, pitch_angle=20.0):
    """ computes the maximum k value for a given teeth count and pitch_angle
        so that no undercut occurs.
    """
    x = sin(radians(pitch_angle))
    return 0.5 * teeth * x * x

def undercut_min_angle(teeth, k=1.0):
    """ computes the minimum pitch angle, to that the given teeth count (and
        profile shift) cause no undercut.
    """
    return degrees(asin(min(0.856, sqrt(2.0*k/teeth))))    # max 59.9 deg

def have_undercut(teeth, pitch_angle=20.0, k=1.0):
    """ returns true if the specified number of teeth would
        cause an undercut.
    """
    return (teeth < undercut_min_teeth(pitch_angle, k))

## gather all basic gear calculations in one place
def gear_calculations(num_teeth, circular_pitch, pressure_angle, clearance=0, ring_gear=False, profile_shift=0.):
    """ Put base calcs for spur/ring gears in one place.
        - negative profile shifting helps against undercut. 
    """
    diametral_pitch = pi / circular_pitch
    pitch_diameter = num_teeth / diametral_pitch
    pitch_radius = pitch_diameter / 2.0
    addendum = 1 / diametral_pitch
    #dedendum = 1.157 / diametral_pitch # auto calc clearance
    dedendum = addendum*1.25
    dedendum *= 1+profile_shift
    addendum *= 1-profile_shift
    if ring_gear:
        addendum = addendum + clearance # our method
    else:
        dedendum = dedendum + clearance # our method
    #
    #
    base_radius = pitch_diameter * cos(radians(pressure_angle)) / 2.0
    outer_radius = pitch_radius + addendum
    root_radius =  pitch_radius - dedendum
    # Tooth thickness: Tooth width along pitch circle.
    tooth_thickness  = ( pi * pitch_diameter ) / ( 2.0 * num_teeth )
    # we don't use these
    working_depth = 2 / diametral_pitch
    whole_depth = 2.157 / diametral_pitch
    #outside_diameter = (num_teeth + 2) / diametral_pitch
    #
    return (pitch_radius, base_radius,
            addendum, dedendum, outer_radius, root_radius,
            tooth_thickness
            )

def pulley_values(pitch):
    # Sélection basée sur le pas (comme précédemment décrit)
    if pitch == 2:
        return (0.15, 0.25, 0.55, 1.1, 0.7)
    elif pitch == 2.5:
        return (0.2, 0.3, 0.6, 1.3, 1)
    elif pitch == 5:
        return (0.4, 0.6, 1, 1.8, 1.8)
    elif pitch == 10:
        return (0.6, 0.8, 2, 3.2, 3.5)
    elif pitch == 20:
        return (0.8, 1, 2.87, 5.7, 6.5)
    
def pulley_calculations(teeth, pitch):
    ri, re, Sp, hd, tooth_width = pulley_values(pitch)
    
    pitch_radius = (teeth * pitch) /np.pi/2 # Rayon primitif
    outer_radius= pitch_radius - (Sp/2) # Rayon externe
    root_radius=outer_radius-hd # Rayon interne
   
    return (pitch_radius, outer_radius, root_radius)

def generate_rack_points(tooth_count, pitch, addendum, pressure_angle,
                       rack_base_height, tab_length, clearance=0, draw_guides=False):
        """ Return path (suitable for svg) of the Rack gear.
            - rack gear uses straight sides
                - involute on a circle of infinite radius is a simple linear ramp
            - the meshing circle touches at y = 0, 
            - the highest elevation of the teeth is at y = +addendum
            - the lowest elevation of the teeth is at y = -addendum-clearance
            - the rack_base_height extends downwards from the lowest elevation.
            - we generate this middle tooth exactly centered on the y=0 line.
              (one extra tooth on the right hand side, if number of teeth is even)
        """
        spacing = 0.5 * pitch # rolling one pitch distance on the spur gear pitch_diameter.
        # roughly center rack in drawing, exact position is so that it meshes
        # nicely with the spur gear.
        # -0.5*spacing has a gap in the center.
        # +0.5*spacing has a tooth in the center.
        fudge = +0.5 * spacing

        tas  = tan(radians(pressure_angle)) * addendum
        tasc = tan(radians(pressure_angle)) * (addendum+clearance)
        base_top = addendum+clearance
        base_bot = addendum+clearance+rack_base_height

        x_lhs = -pitch * int(0.5*tooth_count-.5) - spacing - tab_length - tasc + fudge
        #inkex.utils.debug("angle=%s spacing=%s"%(pressure_angle, spacing))
        # Start with base tab on LHS
        points = [] # make list of points
        points.append((x_lhs, base_bot))
        points.append((x_lhs, base_top))
        x = x_lhs + tab_length+tasc

        # An involute on a circle of infinite radius is a simple linear ramp.
        # We need to add curve at bottom and use clearance.
        for i in range(tooth_count):
            # move along path, generating the next 'tooth'
            # pitch line is at y=0. the left edge hits the pitch line at x
            points.append((x-tasc, base_top))
            points.append((x+tas, -addendum))
            points.append((x+spacing-tas, -addendum))
            points.append((x+spacing+tasc, base_top)) 
            x += pitch
        x -= spacing # remove last adjustment
        # add base on RHS
        x_rhs = x+tasc+tab_length
        points.append((x_rhs, base_top))
        points.append((x_rhs, base_bot))
        # We don't close the path here. Caller does it.
        # points.append((x_lhs, base_bot))

        # Draw line representing the pitch circle of infinite diameter
        guide_path = None
        if draw_guides:
            p = []
            p.append( (x_lhs + 0.5 * tab_length, 0) )
            p.append( (x_rhs - 0.5 * tab_length, 0) )
            guide_path = points_to_svgd(p)
        # return points ready for use in an SVG 'path'
        return (points, guide_path)

def generate_spur_points(teeth, base_radius, pitch_radius, outer_radius, root_radius, accuracy_involute, accuracy_circular):
    """Génère les points pour le tracé SVG d'une roue dentée."""
    half_thick_angle = np.pi / (2.0 * teeth)
    pitch_to_base_angle = involute_intersect_angle(base_radius, pitch_radius)
    pitch_to_outer_angle = involute_intersect_angle(base_radius, outer_radius) - pitch_to_base_angle

    start_involute_radius = max(base_radius, root_radius)
    radii = linspace(start_involute_radius, outer_radius, accuracy_involute)
    angles = [involute_intersect_angle(base_radius, r) for r in radii]

    centers = [(x * two_pi / float(teeth)) for x in range(teeth)]
    points = []

    for c in centers:
        pitch1 = c - half_thick_angle
        base1 = pitch1 - pitch_to_base_angle
        offsetangles1 = [base1 + x for x in angles]
        points1 = [point_on_circle(radii[i], offsetangles1[i]) for i in range(len(radii))]

        pitch2 = c + half_thick_angle
        base2 = pitch2 + pitch_to_base_angle
        offsetangles2 = [base2 - x for x in angles]
        points2 = [point_on_circle(radii[i], offsetangles2[i]) for i in range(len(radii))]

        points_on_outer_radius = [point_on_circle(outer_radius, x) for x in linspace(offsetangles1[-1], offsetangles2[-1], accuracy_circular)]

        if root_radius > base_radius:
            pitch_to_root_angle = pitch_to_base_angle - involute_intersect_angle(base_radius, root_radius)
            root1 = pitch1 - pitch_to_root_angle
            root2 = pitch2 + pitch_to_root_angle
            points_on_root = [point_on_circle(root_radius, x) for x in linspace(root2, root1 + (two_pi / float(teeth)), accuracy_circular)]
            p_tmp = points1 + points_on_outer_radius[1:-1] + points2[::-1] + points_on_root[1:-1]
        else:
            points_on_root = [point_on_circle(root_radius, x) for x in linspace(base2, base1 + (two_pi / float(teeth)), accuracy_circular)]
            p_tmp = points1 + points_on_outer_radius[1:-1] + points2[::-1] + points_on_root

        points.extend(p_tmp)
    return points

def generate_pulley_points(teeth, pitch, Re, Ri):
    # Sélection des valeurs en fonction du pas
    ri, re, Sp, hd, tooth_width = pulley_values(pitch)

    flank_angle_rad = np.radians(25) # Angle des dents de 25°

    thick_angle= two_pi / teeth # angle d'une dent
    ext_angle = tooth_width / Re  #  angle correspondant à la largeur externe de la dent
    
    bf=thick_angle-ext_angle
    Lbf=bf*Re
    rx=(Lbf/2)/np.sin(flank_angle_rad)
    dpep=sin(flank_angle_rad)*(rx-hd)

    de=dpep/Ri
    flank_angle=(bf-2*de)/2

    points = []
    for tooth in range(teeth):
        c = tooth * two_pi / teeth
        # Points de la dent (extérieur)
        Ce_left = point_on_circle(Re, c )
        Ce_right = point_on_circle(Re, c + ext_angle)
        # Points de la dent (intérieur)
        Ci_left = point_on_circle(Ri, c + ext_angle + flank_angle)
        Ci_right = point_on_circle(Ri, c - flank_angle)
        
        points.extend([Ci_right,Ce_left,Ce_right,Ci_left])

    return points

def generate_spokes_path(root_radius, spoke_width, spoke_count, mount_radius, mount_hole,
                         unit_factor, unit_label):
    """ 
    Trace les rayons
    donne un ensemble de contraintes
        - générer le chemin SVG pour les rayons de l'engrenage
        - se situe entre mount_radius (trou intérieur) et root_radius (base des dents)
        - la largeur des rayons définit également l'espacement au niveau du root_radius
        - le mount_radius est ajusté pour que les rayons s'adaptent s'il y a de la place
        - si pas de place (collision) alors les rayons ne sont pas dessinés
    """
    # Spokes
    collision = False # assume we draw spokes
    messages = []     # messages to send back about changes.
    path = ''
    r_outer = root_radius - spoke_width
    # checks for collision with spokes
    # check for mount hole collision with inner spokes
    if mount_radius <= mount_hole/2:
        adj_factor = (r_outer - mount_hole/2) / 5
        if adj_factor < 0.1:
            # not enough reasonable room
            collision = True
        else:
            mount_radius = mount_hole/2 + adj_factor # small fix
            messages.append("Support de montage trop petit. Augmentation automatique à %2.2f%s." % (mount_radius/unit_factor*2, unit_label))            
    # then check to see if cross-over on spoke width
    if spoke_width * spoke_count +0.5 >= two_pi * mount_radius:
        adj_factor = 1.2 # wrong value. its probably one of the points distances calculated below
        mount_radius += adj_factor
        messages.append("Trop de rayons. Support de montage augmenté de %2.3f%s" % (adj_factor/unit_factor, unit_label))
    
    # check for collision with outer rim
    if r_outer <= mount_radius:
        # not enough room to draw spokes so cancel
        collision = True
    if collision: # don't draw spokes if no room.
        messages.append("Pas assez d'espace pour les rayons. Diminuez le diamètre.")
    else: # draw spokes
        for i in range(spoke_count):
            points = []
            start_a, end_a = i * two_pi / spoke_count, (i+1) * two_pi / spoke_count
            # inner circle around mount
            asin_factor = spoke_width/mount_radius/2
            # check if need to clamp radius
            asin_factor = max(-1.0, min(1.0, asin_factor)) # no longer needed - resized above
            a = asin(asin_factor)
            points += [ point_on_circle(mount_radius, start_a + a), point_on_circle(mount_radius, end_a - a)]
            # is inner circle too small
            asin_factor = spoke_width/r_outer/2
            # check if need to clamp radius
            asin_factor = max(-1.0, min(1.0, asin_factor)) # no longer needed - resized above
            a = asin(asin_factor)
            points += [point_on_circle(r_outer, end_a - a), point_on_circle(r_outer, start_a + a) ]

            path += (
                    "M %f,%f" % points[0] +
                    "A  %f,%f %s %s %s %f,%f" % tuple((mount_radius, mount_radius, 0, 0 if spoke_count!=1 else 1, 1 ) + points[1]) +
                    "L %f,%f" % points[2] +
                    "A  %f,%f %s %s %s %f,%f" % tuple((r_outer, r_outer, 0, 0 if spoke_count!=1 else 1, 0 ) + points[3]) +
                    "Z"
                    )
    return (path, messages)

class Gears(inkex.EffectExtension):
    def __init__(self):
        inkex.Effect.__init__(self)
        # * 1-onglet denture
        self.arg_parser.add_argument("-t", "--teeth", type=int, default=24, help="Number of teeth")
        self.arg_parser.add_argument("-u", "--units", default='mm', help="Units this dialog is using")
        self.arg_parser.add_argument("-ty", "--type", type=str, default="dev", help="Type de la denture")        
        self.arg_parser.add_argument("-d", "--dimension", type=float, default=1.0, help="Tooth size, depending on system (which defaults to CP)")
        self.arg_parser.add_argument("-a", "--angle", type=float, default=20.0, help="Pressure Angle (common values: 14.5, 20, 25 degrees)")
        self.arg_parser.add_argument("-i", "--internal_ring", type=inkex.Boolean, default=False, help="Ring (or Internal) gear style (default: normal spur gear)")
        self.arg_parser.add_argument("-pa", "--pas", type=float, default="5", help="Pas pour la denture métrique")
        self.arg_parser.add_argument("-af", "--ajout_flanc", type=inkex.Boolean, default=False, help="Ajouter 2 flancs à coller de chaque coté de la roue dentée.")
        # * 2-onglet perçage
        self.arg_parser.add_argument("-ho", "--hole", type=inkex.Boolean, default=True, help="Hole or not that is the question")
        self.arg_parser.add_argument("-sh", "--shape", type=str, default="Rectangulaire", help="Shape of the hole")
        self.arg_parser.add_argument("-mh", "--mount_hole", type=float, default=4.42, help="Mount hole diameter")
        self.arg_parser.add_argument("-hw", "--hole_width", type=float, default=2.9, help="Width of rectangular hole")
        self.arg_parser.add_argument("-hl", "--hole_length", type=float, default=2.9, help="Length of rectangular hole") 
        self.arg_parser.add_argument("-cp", "--CarreParfait", type=inkex.Boolean, default=True, help="CarreParfait")
        self.arg_parser.add_argument("-ba", "--BarreAxe", type=inkex.Boolean, default=True, help="BarreAxe")
        self.arg_parser.add_argument("-ax", "--LongueurAxe", type=float, default=6, help="Longueur de l'axe")
        self.arg_parser.add_argument("-se", "--servo", type=str, default="HS422", help="shape of servo")
        self.arg_parser.add_argument("-rs", "--RoueServo", type=inkex.Boolean, default=True, help="dessine une roue pour fixer le servo ou non")
        self.arg_parser.add_argument("-dc", "--DiametreCercle", type=float, default=20, help="Diamètre du cercle de fixation du servo")
        # * 3-onglet Rayons
        self.arg_parser.add_argument("-hp", "--draw_spoke", type=inkex.Boolean, default=True, help="Spoke or not")
        self.arg_parser.add_argument("-sc", "--spoke_count", type=int, default=3, help="Spokes count")
        self.arg_parser.add_argument("-sw", "--spoke_width", type=float, default=5, help="Spoke width")
        self.arg_parser.add_argument("-md", "--mount_diameter", type=float, default=15, help="Mount support diameter")
        # * 4-onglet crémaillère
        self.arg_parser.add_argument("-r", "--draw_rack", type=inkex.Boolean, default=False, help="Draw rack gear instead of spur gear")
        self.arg_parser.add_argument("-rl", "--rack_teeth_length", type=int, default=12, help="Length (in teeth) of rack")
        self.arg_parser.add_argument("-rh", "--rack_base_height", type=float, default=8, help="Height of base of rack")
        self.arg_parser.add_argument("-rt", "--rack_base_tab", type=float, default=14, help="Length of tabs on ends of rack") 
        # * 5-Onglet "Materiel et matériaux"
        self.arg_parser.add_argument("-b", "--bymaterial", type=inkex.Boolean, default=True, help="Are kerf define by material")
        self.arg_parser.add_argument("-ma", "--materiaux", type=float, default=0.15, help="Kerf size define by material")
        self.arg_parser.add_argument("-k", "--kerf_size", type=float, default=0.0, help="Kerf size - amount lost to laser for this material. 0 = loose fit")
        self.arg_parser.add_argument("-g", "--linewidth", type=inkex.Boolean, default=True, help="Use the kerf value as the drawn line width")
        self.arg_parser.add_argument("-je", "--jeu", type=float, default=0.15, help="jeu")
        self.arg_parser.add_argument("-em", "--epaisseur_matos", type=float, default=0.15, help="Epaisseur du matériau")                 
        # * 6-onglet options avancées
        self.arg_parser.add_argument("-x", "--centercross", type=inkex.Boolean, default=False, help="Draw cross in center")
        self.arg_parser.add_argument("-c", "--pitchcircle", type=inkex.Boolean, default=False, help="Draw pitch circle (for mating)")
        self.arg_parser.add_argument("-an", "--annotation", type=inkex.Boolean, default=False, help="Draw annotation text")
        self.arg_parser.add_argument("-cl", "--clearance", type=float, default=0.0, help="Clearance between bottom of gap of this gear and top of tooth of another") # Clearance: Radial distance between top of tooth on one gear to bottom of gap on another.
        self.arg_parser.add_argument("-p", "--profile_shift", type=float, default=20.0, help="Profile shift [in percent of the module]. Negative values help against undercut")
        self.arg_parser.add_argument("-A", "--accuracy", type=int, default=0, help="Accuracy of involute: automatic: 5..20 (default), best: 20(default), medium 10, low: 5; good acuracy is important with a low tooth count")
        self.arg_parser.add_argument("-ua", "--undercut_alert", type=inkex.Boolean, default=False, help="Let the user confirm a warning dialog if undercut occurs. This dialog also shows helpful hints against undercut")
        
        self.arg_parser.add_argument("-at", "--active_tab", default='', help="Active tab. Not used now.")
        
    def add_text(self, node, text, position, text_height=12, Attention=False):
        """ Create and insert a single line of text into the svg under node.
            - use 'text' type and label as anootation
            - where color is Ponoko Orange - so ignored when lasercutting or red if there is a warning
        """
        global PremiereLigne
        if Attention:
            CoulText="#FF0405"
        else :
            CoulText="#F6921E"
            
        line_style = {'font-size': '%dpx' % text_height, 'font-style':'normal', 'font-weight': 'normal',
                     'fill': '%s' % CoulText, 'font-family': 'Bitstream Vera Sans,sans-serif',
                     'text-anchor': 'start'}
        line_attribs = {inkex.addNS('label','inkscape'): 'Annotation',
                       'style':  str(inkex.Style(line_style)),
                       'x': str(position[0]),
                       'y': str((position[1]))
                       }
        line = etree.SubElement(node, inkex.addNS('text','svg'), line_attribs)
        line.text = text

    def calc_unit_factor(self):
        """ return the scale factor for all dimension conversions.
            - The document units are always irrelevant as
              everything in inkscape is expected to be in 90dpi pixel units
        """
        # namedView = self.document.getroot().find(inkex.addNS('namedview', 'sodipodi'))
        # doc_units = uutounit(self, 1.0, namedView.get(inkex.addNS('document-units', 'inkscape')))
        dialog_units = uutounit(self, 1.0, self.options.units)
        unit_factor = 1.0 / dialog_units
        return unit_factor

    def calc_circular_pitch(self):
        """ We use math based on circular pitch.
            Expressed in inkscape units which is 90dpi 'pixel' units.
        """
        dimension = self.options.dimension
        circular_pitch = dimension * pi / 25.4

        # circular_pitch defines the size in inches.
        # We divide the internal inch factor (px = 90dpi), to remove the inch 
        # unit.
        # The internal inkscape unit is always px, 
        # it is independent of the doc_units!
        return circular_pitch / uutounit(self, 1.0, 'in')

    def effect(self):
        """ Calculate Gear factors from inputs.
            - Make list of radii, angles, and centers for each tooth and 
              iterate through them
            - Turn on other visual features e.g. cross, rack, annotations, etc
        """
        config = ConfigParser()
        stroke_color_teeth = '#663300'
        stroke_color_hole = '#0000FF'
        stroke_color_ring = '#660066'
        stroke_color_spoke = '#006633'
        stroke_color_rect = '#006633'
        stroke_color_guide = '#FF6600'
        path_stroke='#000000'
        path_fill   = 'none'     # no fill - just a line
        #
        warnings = [] # list of extra messages to be shown in annotations
        # calculate unit factor for units defined in dialog. 
        unit_factor = self.calc_unit_factor()
        # User defined options
        teeth = self.options.teeth
        # Angle of tangent to tooth at circular pitch wrt radial line.
        angle = self.options.angle 
        type=self.options.type
        pas=self.options.pas
        # Clearance: Radial distance between top of tooth on one gear to 
        # bottom of gap on another.
        clearance = self.options.clearance * unit_factor
        hole=self.options.hole
        shape=self.options.shape
        hole_width=self.options.hole_width * unit_factor
        hole_length=self.options.hole_length * unit_factor
        mount_hole = self.options.mount_hole * unit_factor
        servo=self.options.servo
        jeu=self.options.jeu * unit_factor
        epaisseur_matos=self.options.epaisseur_matos * unit_factor
        if self.options.bymaterial:
            kerf=self.options.materiaux * unit_factor
        else:
            kerf=self.options.kerf_size * unit_factor
        path_stroke_width  = kerf # default line width = kerf
        path_stroke_light  = uutounit(self, 0.05, 'mm') # guides are thinner
        DiametreCercle=self.options.DiametreCercle * unit_factor    
        cote=epaisseur_matos-kerf+jeu
        # for spokes
        mount_radius = self.options.mount_diameter * 0.5 * unit_factor
        spoke_count = self.options.spoke_count
        if not(self.options.draw_spoke) or  type=="T":
            spoke_count=0
        spoke_width = self.options.spoke_width * unit_factor
        # visible guide lines
        centercross = self.options.centercross # draw center or not (boolean)
        pitchcircle = self.options.pitchcircle # draw pitch circle or not (boolean)
        if shape=="Rectangulaire":
            mount_hole=sqrt( hole_width**2 + hole_length**2 )
            if self.options.CarreParfait:
                mount_hole=sqrt(2*(cote))
        if shape=="Empreinte" :
            config.read('engrenage.ini')
            servoDiameter = config.getfloat(servo, 'diametre')
            servoPath=config.get(servo, 'd')
            mount_hole=servoDiameter
        # Accuracy of teeth curves
        accuracy_involute = 20 # Number of points of the involute curve
        accuracy_circular = 9  # Number of points on circular parts
        if self.options.accuracy is not None:
            if self.options.accuracy == 0:  
                # automatic
                if   teeth < 10: accuracy_involute = 20
                elif teeth < 30: accuracy_involute = 12
                else:            accuracy_involute = 6
            else:
                accuracy_involute = self.options.accuracy
            accuracy_circular = max(3, int(accuracy_involute/2) - 1) # never less than three
        pitch = self.calc_circular_pitch()
        # Replace section below with this call to get the combined gear_calculations() above
        if type=="dev":
            (pitch_radius, base_radius, addendum, dedendum,
            outer_radius, root_radius, tooth) = gear_calculations(teeth, pitch, angle, clearance, self.options.internal_ring, self.options.profile_shift*0.01)
        else:
            (pitch_radius, outer_radius, root_radius) = pulley_calculations(teeth, pas)
            self.options.draw_rack=False

        # Detect Undercut of teeth
        if have_undercut(teeth, angle, 1.0):
            min_teeth = int(ceil(undercut_min_teeth(angle, 1.0)))
            min_angle = undercut_min_angle(teeth, 1.0) + .1
            max_k = undercut_max_k(teeth, angle)
            msg = "Attention !\nAvertissement de sous-coupe !\nCet engrenage (%d dents) ne fonctionnera pas bien.\nEssayez un nombre de dents de %d ou plus,\nou un angle de pression de %s [deg] ou plus,\nou essayez un décalage de profil de %d %%.\nOu d'autres combinaisons." % (teeth, min_teeth, locale.format_string("%.1f", min_angle).rstrip('0').rstrip(','), int(100. * max_k) - 100.)            
            self.options.annotation=True
            # alas annotation cannot handle the degree symbol.  Also it ignore
            # newlines.
            # so split and make a list
            warnings.extend(msg.split("\n"))

        pathSpoke=""
        pathHole=""
        pathRing = ""
        pathRect = ""
        # All base calcs done. Start building gear
        if type=="dev":
            points = generate_spur_points(teeth, base_radius, pitch_radius, outer_radius, root_radius, accuracy_involute, accuracy_circular)
        else :
            points=generate_pulley_points(teeth, pas, outer_radius, root_radius)

        pathTeeth = points_to_svgd( points )    
        bbox_center = points_to_bbox_center( points )

        if not self.options.internal_ring:  # only draw internals if spur gear
            # dessin des rayons
            if self.options.RoueServo:# s'assure que les carrés de fixation soient dans de la matière
                if mount_radius<10:
                    mount_radius=10
            spokes_path, msg = generate_spokes_path(root_radius, spoke_width, spoke_count, mount_radius, mount_hole,
                                                    unit_factor, self.options.units)
            warnings.extend(msg)
            # Spokes (add to current path)
            pathSpoke = spokes_path
            if hole:
                if shape=="Rond":
                    # Draw mount hole
                    # A : rx,ry  x-axis-rotation, large-arch-flag, sweepflag  x,y
                    r = mount_hole / 2
                    pathHole= (
                            "M %f,%f" % (0,r) +
                            "A  %f,%f %s %s %s %f,%f" % (r,r, 0,0,0, 0,-r) +
                            "A  %f,%f %s %s %s %f,%f" % (r,r, 0,0,0, 0,r) 
                            )
                if shape=="Rectangulaire":   
                    if self.options.CarreParfait:
                        hole_length=hole_width=cote
                    pathHole=(
                            "M %f,%f" % (0, hole_length/2) +
                            "L %f,%f" % (hole_width/2, hole_length/2)+
                            "L %f,%f" % (hole_width/2, -hole_length/2) +
                            "L %f,%f" % (-hole_width/2, -hole_length/2)+
                            "L %f,%f" % (-hole_width/2, hole_length/2)+
                            "Z"
                            )

                if shape=="Empreinte":
                    pathHole= servoPath
        else:
            # its a ring gear // pas de trou central
            # which only has an outer ring where width = spoke width
            r = outer_radius + spoke_width
            pathRing= (
                    "M %f,%f" % (0,r) +
                    "A  %f,%f %s %s %s %f,%f" % (r,r, 0,0,0, 0,-r) +
                    "A  %f,%f %s %s %s %f,%f" % (r,r, 0,0,0, 0,r) 
                    )
        
        # Embed gear in group to make animation easier:
        #  Translate group, Rotate path.
        t = 'translate(' + str( self.svg.namedview.center[0] ) + ',' + str( self.svg.namedview.center[1] ) + ')'
        g_attribs = { inkex.addNS('label','inkscape'):'Gear' + str( teeth ),
                      inkex.addNS('transform-center-x','inkscape'): str(-bbox_center[0]),
                      inkex.addNS('transform-center-y','inkscape'): str(-bbox_center[1]),
                      'transform':t,
                      'info':'N:'+str(teeth)+'; Pitch:'+ str(pitch) + '; Pressure Angle: '+str(angle) }
        # add the group to the current layer
        g = etree.SubElement(self.svg.get_current_layer(), 'g', g_attribs )

        # Create gear path under top level group
        # Définir les styles spécifiques pour chaque path
        styles = {
            'pathTeeth': {'stroke': stroke_color_teeth, 'fill': 'none', 'stroke-width': path_stroke_width},
            'pathHole': {'stroke': stroke_color_hole, 'fill': 'none', 'stroke-width': path_stroke_width},
            'pathRing': {'stroke': stroke_color_ring, 'fill': 'none', 'stroke-width': path_stroke_width},
            'pathSpoke': {'stroke': stroke_color_spoke, 'fill': 'none', 'stroke-width': path_stroke_width},
            'pathRect': {'stroke': stroke_color_rect, 'fill': 'none', 'stroke-width': path_stroke_width}
        }
        paths = {
            'pathTeeth': pathTeeth,
            'pathHole': pathHole,
            'pathRing': pathRing,
            'pathSpoke': pathSpoke,
            'pathRect': pathRect 
        }
        # Itérer sur chaque path et appliquer son style spécifique
        for path_name, path_data in paths.items():
            style = styles[path_name]
            style_str = str(inkex.Style(style))
            gear_attribs = {'style': style_str, 'd': path_data}
            etree.SubElement(g, inkex.addNS('path', 'svg'), gear_attribs)
        
        if self.options.RoueServo or (self.options.ajout_flanc and self.options.type=="T"):
            #trace les carrés sur l'engrenage et les flancs
            draw_SVG_rect(g,-(5+cote),-cote/2,cote,cote,'RectFixationGauche',styles['pathRect'])
            draw_SVG_rect(g,5,-cote/2,cote,cote,'RectFixationDroit',styles['pathRect'])
            
        bbox_points = list(points_to_bbox(points))
        
        if self.options.CarreParfait and self.options.BarreAxe:
            # trace l'axe
            xAxe=DiametreCercle/2+2
            yAxe=-DiametreCercle/2
            LargeurAxe=epaisseur_matos+kerf
            draw_SVG_rect(g,xAxe,yAxe,LargeurAxe,self.options.LongueurAxe,'RectFixationDroit',styles['pathRect'])
            bbox_points[2] = bbox_points[2] + LargeurAxe
            bbox_points = tuple(bbox_points)
        
            
        if self.options.RoueServo:            
            # trace la roue de liaison avec le servo et ses fixations
            DiametreCercleMin=2*(hypot(cote,cote)+5+2)
            if DiametreCercle<DiametreCercleMin:
                DiametreCercle=DiametreCercleMin
            RayonCercle=DiametreCercle/2    
            t2 = f'translate({bbox_points[2]+self.svg.namedview.center[0] +RayonCercle+2},{-bbox_points[3]+self.svg.namedview.center[1] +RayonCercle})'
            g_attribs2 = { inkex.addNS('label','inkscape'):'Fixation servomoteur',
                            inkex.addNS('transform-center-x','inkscape'): str(-bbox_center[0]),
                            inkex.addNS('transform-center-y','inkscape'): str(-bbox_center[1]),
                        'transform':t2}
            g2 = etree.SubElement(self.svg.get_current_layer(), 'g', g_attribs2 )            
            draw_SVG_rect(g2,-(5+cote),-cote/2,cote,cote,'RectFixationGauche',styles['pathRect'])
            draw_SVG_rect(g2,5,-cote/2,cote,cote,'RectFixationDroit',styles['pathRect'])
            draw_SVG_circle(g2,RayonCercle,0,0,'CercleFixation',styles['pathTeeth'])
            LongueurRectFix=2*epaisseur_matos+kerf
            LargeurRectFix=epaisseur_matos+kerf
            draw_SVG_rect(g2,-LongueurRectFix/2,-5-LargeurRectFix,LongueurRectFix,LargeurRectFix,'RectFix1',styles['pathRect'])
            draw_SVG_rect(g2,-LongueurRectFix/2,+5,LongueurRectFix,LargeurRectFix,'RectFix2',styles['pathRect'])
            config.read('engrenage.ini')
            servoPath=config.get(servo, 'd')
            style = styles['pathHole']
            style_str = str(inkex.Style(style))
            gear_attribs2 = {'style': style_str, 'd': servoPath}
            etree.SubElement(g2, inkex.addNS('path', 'svg'), gear_attribs2)
        
        if self.options.ajout_flanc and (self.options.type=="T" ):
            #trace les flancs à coller de chaque coté de la roue dentée
            if self.options.RoueServo:
                t3 = f'translate({bbox_points[2]+self.svg.namedview.center[0] +DiametreCercle+outer_radius+3},{-bbox_points[3]+self.svg.namedview.center[1]+outer_radius })'
                LongueurBarre=epaisseur_matos*4
            else:
                t3 = f'translate({bbox_points[2]+self.svg.namedview.center[0] +outer_radius},{-bbox_points[3]+self.svg.namedview.center[1] +outer_radius})'
                LongueurBarre=epaisseur_matos*3
            g_attribs3 = { inkex.addNS('label','inkscape'):'Flancs',
                            inkex.addNS('transform-center-x','inkscape'): str(-bbox_center[0]),
                            inkex.addNS('transform-center-y','inkscape'): str(-bbox_center[1]),
                        'transform':t3}
            g3 = etree.SubElement(self.svg.get_current_layer(), 'g', g_attribs3 ) 
            draw_SVG_circle(g3,outer_radius,0,0,'Flanc1',styles['pathTeeth'])
            draw_SVG_circle(g3,outer_radius,outer_radius*2,0,'Flanc2',styles['pathTeeth'])
            draw_SVG_rect(g3,-(5+cote),-cote/2,cote,cote,'RectFixationGauche',styles['pathRect'])
            draw_SVG_rect(g3,5,-cote/2,cote,cote,'RectFixationDroit',styles['pathRect'])
            draw_SVG_rect(g3,-(5+cote)+outer_radius*2,-cote/2,cote,cote,'RectFixationGauche',styles['pathRect'])
            draw_SVG_rect(g3,5+outer_radius*2,-cote/2,cote,cote,'RectFixationDroit',styles['pathRect'])
            style = styles['pathHole']
            style_str = str(inkex.Style(style))
            gear_attribs3 = {'style': style_str, 'd': pathHole}
            etree.SubElement(g3, inkex.addNS('path', 'svg'), gear_attribs3)
            # trace les barres de fixation
            g4 = etree.SubElement(self.svg.get_current_layer(), 'g', g_attribs3 ) 
            xBarre=3*outer_radius
            yBarre=-outer_radius
            LargeurBarre=(epaisseur_matos+kerf)*2
            draw_SVG_rect(g4,xBarre,yBarre,LargeurBarre,LongueurBarre,'RectFixationDroit',styles['pathRect'])
            style = styles['pathRect']
            style_str = str(inkex.Style(style))
            pathbarre = "M %.3f,%.3f v %.3f" % (xBarre+epaisseur_matos+kerf,yBarre,LongueurBarre)
            gear_attribs4 = {'style': style_str, 'd': pathbarre}
            etree.SubElement(g4, inkex.addNS('path', 'svg'), gear_attribs4)            
                       
        # Add center
        if centercross:
            style = {'stroke': stroke_color_guide, 'fill': path_fill,
                     'stroke-width': path_stroke_light}
            cs = str(pitch / 3)  # centercross length
            d = 'M-'+cs+',0L'+cs+',0M0,-'+cs+'L0,'+cs  # 'M-10,0L10,0M0,-10L0,10'
            center_attribs = {inkex.addNS('label', 'inkscape'): 'Center cross',
                              'style': str(inkex.Style(style)), 'd': d}
            center = etree.SubElement(
                g, inkex.addNS('path', 'svg'), center_attribs)

        # Add pitch circle (for mating)
        if pitchcircle:
            style = { 'stroke': stroke_color_guide, 'fill': path_fill, 'stroke-width': path_stroke_light }
            draw_SVG_circle(g, pitch_radius, 0, 0, 'Pitch circle', style)

        # Add Rack (below)
        if self.options.draw_rack:
            rack_base_height = self.options.rack_base_height * unit_factor
            tab_width = self.options.rack_base_tab * unit_factor
            tooth_count = self.options.rack_teeth_length
            (points, guide_path) = generate_rack_points(tooth_count, pitch, addendum, angle,
                                                        rack_base_height, tab_width, clearance, pitchcircle)
            path = points_to_svgd(points)
            # position below Gear, so that it meshes nicely
            xoff = (-0.5, -0.25, 0, -0.75)[teeth % 4] * pitch
            t = 'translate(' + str( xoff ) + ',' + str( pitch_radius+2 ) + ')'
            g_attribs = { inkex.addNS('label', 'inkscape'): 'RackGear' + str(tooth_count),
                          'transform': t }
            rack = etree.SubElement(g, 'g', g_attribs)

            # Create SVG Path for gear
            style = {'stroke': stroke_color_teeth, 'fill': 'none', 'stroke-width': path_stroke_width }
            gear_attribs = { 'style': str(inkex.Style(style)), 'd': path }
            gear = etree.SubElement(
                rack, inkex.addNS('path', 'svg'), gear_attribs)
            if guide_path is not None:
                style2 = { 'stroke': stroke_color_guide, 'fill': 'none', 'stroke-width': path_stroke_light }
                gear_attribs2 = { 'style':  str(inkex.Style(style2)), 'd': guide_path }
                gear = etree.SubElement(
                    rack, inkex.addNS('path', 'svg'), gear_attribs2)

        # Add Annotations (above)
        if self.options.annotation:
            outer_dia = outer_radius * 2
            if self.options.internal_ring:
                outer_dia += 2 * spoke_width
            notes = []
            notes.extend(warnings)
            if len(warnings) > 0:
                Attention=True
            else :
                Attention=False    
            #notes.append('Document (%s) scale conversion = %2.4f' % (self.document.getroot().find(inkex.addNS('namedview', 'sodipodi')).get(inkex.addNS('document-units', 'inkscape')), unit_factor))
            if type=="dev":
                notes.extend([
                    'Dents : %d' % (teeth),
                    'Pas angulaire : %s %s (%s °)' % (locale.format_string("%.2f", pitch / unit_factor).rstrip('0').rstrip(','), self.options.units,locale.format_string("%.1f", 360/teeth).rstrip('0').rstrip(',')),
                    'Module : %s %s' % (locale.format_string("%.2f", pitch_radius * 2 / teeth).rstrip('0').rstrip(','), self.options.units),
                    'Angle de pression : %s °' % (locale.format_string("%.2f", angle).rstrip('0').rstrip(',')),
                    'Diamètre primitif : %s %s' % (locale.format_string("%.2f", pitch_radius * 2 / unit_factor).rstrip('0').rstrip(','), self.options.units),
                    'Diamètre extérieur : %s %s' % (locale.format_string("%.2f", outer_dia / unit_factor).rstrip('0').rstrip(','), self.options.units),
                    'Diamètre de base :  %s %s' % (locale.format_string("%.2f", base_radius * 2 / unit_factor).rstrip('0').rstrip(','), self.options.units),
                    'Diamètre de pied :  %s %s' % (locale.format_string("%.2f",  pitch_radius * 2 * (1-2.5/teeth) ).rstrip('0').rstrip(','), self.options.units),
                    'Hauteur de dent :  %s %s' % (locale.format_string("%.2f",  (dedendum+addendum)/ unit_factor).rstrip('0').rstrip(','), self.options.units),
                    'Épaisseur de dent : %s %s' % (locale.format_string("%.2f", tooth / unit_factor).rstrip('0').rstrip(','), self.options.units),
                    'Saillie : %s %s' % (locale.format_string("%.2f", addendum/ unit_factor).rstrip('0').rstrip(','), self.options.units),
                    'Creux : %s %s' % (locale.format_string("%.2f", dedendum/ unit_factor).rstrip('0').rstrip(','), self.options.units),
                    ])
            else:
                ri, re, Sp, hd, tooth_width = pulley_values(pas)
                notes.extend([
                    'Dents : %d' % teeth,
                    'Pas : %s' % locale.format_string("%.1f", pas),
                    'Diamètre primitif : %s %s' % (locale.format_string("%.2f", pitch_radius * 2 ).rstrip('0').rstrip(','), self.options.units),
                    'Diamètre extérieur : %s %s' % (locale.format_string("%.2f", outer_radius * 2 ).rstrip('0').rstrip(','), self.options.units),
                    'Diamètre intérieur :  %s %s' % (locale.format_string("%.2f", root_radius * 2 ).rstrip('0').rstrip(','), self.options.units),
                    'Hauteur de dent :  %s %s' % (locale.format_string("%.2f", hd), self.options.units),
                    'Largeur de dent : %s %s' % (locale.format_string("%.2f", tooth_width), self.options.units),
                    ])          
            # text height relative to gear size.
            # ranges from 10 to 22 over outer radius size 60 to 360
            text_height = max(10, min(10+(outer_dia-60)/24, 22))
            # position above
            y = - outer_radius - (len(notes)+1) * text_height * 1.2
            haut=y
            x=-outer_dia//2
            largeur=0
            nb_lignes=0
            for note in notes:
                lar=len(note)
                if lar>largeur:
                    largeur=(lar+1)*text_height/2
                nb_lignes+=1    
               
            if Attention:
                rect = etree.SubElement(g, inkex.addNS('rect','svg'))
                # Définir les attributs du rectangle
                rect.set('x', str(x))
                rect.set('y', str((haut - text_height) ))
                rect.set('width', largeur)
                rect.set('height', str(text_height*1.2*nb_lignes))
                rect.set('fill', 'yellow')  # Couleur de fond
                PremiereLigne=False
            for note in notes:
                self.add_text(g, note, [x,y], text_height, Attention)
                y += text_height * 1.2    
                
if __name__ == '__main__':
    Gears().run()
