# -*- coding: utf-8 -*-
"""Procesador HYDA"""

from qgis.core import (QgsGeometry, QgsPointXY, QgsRectangle, QgsWkbTypes)
from qgis.PyQt.QtCore import QVariant
import math


def es_curva_cerrada(geom, tol=2.0):
    if geom.length() == 0:
        return False
    coords = geom.asPolyline()
    if len(coords) < 3:
        return False
    return coords[0].distance(coords[-1]) < tol


def es_pico_real(geom, elev, idx, curvas, r=250):
    if not es_curva_cerrada(geom):
        return False
    coords = geom.asPolyline()
    if len(coords) < 3:
        return False
    
    poly = QgsGeometry.fromPolygonXY([coords])
    bbox = geom.boundingBox()
    bbox_exp = QgsRectangle(bbox.xMinimum()-r, bbox.yMinimum()-r, bbox.xMaximum()+r, bbox.yMaximum()+r)
    ids_c = idx.intersects(bbox_exp)
    
    for fid in ids_c:
        c_inf = curvas[fid]
        if c_inf['elevation'] <= elev:
            continue
        g_sup = c_inf['geometry']
        centro = obtener_centro_curva(g_sup)
        pt_g = QgsGeometry.fromPointXY(centro)
        if poly.contains(pt_g):
            return False
    return True


def obtener_centro_curva(geom):
    c = geom.centroid()
    if c.isEmpty():
        coords = geom.asPolyline()
        x = sum(p.x() for p in coords) / len(coords)
        y = sum(p.y() for p in coords) / len(coords)
        return QgsPointXY(x, y)
    return c.asPoint()


def calc_dir(p1, p2):
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    if dx == 0 and dy == 0:
        return None
    return math.atan2(dy, dx)


def score_dir(p_orig, p_cand, dir_obj):
    if dir_obj is None:
        return 50
    d_cand = calc_dir(p_orig, p_cand)
    if d_cand is None:
        return 0
    diff = abs(d_cand - dir_obj)
    if diff > math.pi:
        diff = 2 * math.pi - diff
    return 100 * (1 - diff / math.pi)


def contar_cruces(p_ini, p_fin, idx, curvas_d, curvas_u, elev_act):
    seg = QgsGeometry.fromPolylineXY([p_ini, p_fin])
    bbox = seg.boundingBox()
    bbox_exp = QgsRectangle(bbox.xMinimum()-50, bbox.yMinimum()-50, bbox.xMaximum()+50, bbox.yMaximum()+50)
    
    ids = idx.intersects(bbox_exp)
    cruces = []
    
    for fid in ids:
        if fid in curvas_u:
            continue
        c_inf = curvas_d[fid]
        if abs(c_inf['elevation'] - elev_act) > 20:
            continue
        if seg.intersects(c_inf['geometry']):
            cruces.append({'idx': fid, 'elev': c_inf['elevation']})
    
    return len(cruces), cruces


def contar_menores(pt, idx, curvas, elev_ref, r=30.0):
    bbox = QgsRectangle(pt.x()-r, pt.y()-r, pt.x()+r, pt.y()+r)
    ids = idx.intersects(bbox)
    cnt = 0
    pt_g = QgsGeometry.fromPointXY(pt)
    
    for fid in ids:
        c_inf = curvas[fid]
        if c_inf['elevation'] >= elev_ref:
            continue
        if c_inf['geometry'].distance(pt_g) <= r:
            cnt += 1
    return cnt


def pto_salida_cresta(c_pico, g_pico, e_pico, dir_gen, idx, curvas, c_sig):
    coords = g_pico.asPolyline()
    if len(coords) < 3:
        return c_pico
    
    mejor_pt = None
    mejor_sc = -999999
    paso = max(1, len(coords) // 20)
    
    for i in range(0, len(coords), paso):
        pt = coords[i]
        sc_d = score_dir(c_pico, pt, dir_gen)
        n_bajas = contar_menores(pt, idx, curvas, e_pico, r=30.0)
        sc_alt = -n_bajas * 10
        
        d_min_sig = float('inf')
        for c_s in c_sig:
            if c_s['elevation'] > e_pico:
                d = c_s['geometry'].distance(QgsGeometry.fromPointXY(pt))
                d_min_sig = min(d_min_sig, d)
        
        sc_prox = 100 / (1 + d_min_sig / 10.0) if d_min_sig < float('inf') else 0
        sc_tot = sc_d * 2.0 + sc_alt * 1.0 + sc_prox * 2.5
        
        if sc_tot > mejor_sc:
            mejor_sc = sc_tot
            mejor_pt = pt
    
    return mejor_pt if mejor_pt else c_pico


def buscar_curva(pt_act, idx, curvas_d, curvas_u, elev_act, radio, dir_gen):
    bbox = QgsRectangle(pt_act.x()-radio, pt_act.y()-radio, pt_act.x()+radio, pt_act.y()+radio)
    ids = idx.intersects(bbox)
    
    elevs_obj = [elev_act + 1, elev_act]
    
    # Separar candidatas por elevación ANTES de procesar geometría
    cands_por_elev = {elev_act + 1: [], elev_act: []}
    
    for fid in ids:
        if fid in curvas_u:
            continue
        c_inf = curvas_d[fid]
        if c_inf['elevation'] not in elevs_obj:
            continue
        
        # Guardar en su grupo de elevación
        cands_por_elev[c_inf['elevation']].append((fid, c_inf))
    
    # Procesar PRIMERO elevación+1, LUEGO elevación actual
    for e_obj in elevs_obj:
        cands = []
        
        for fid, c_inf in cands_por_elev[e_obj]:
            c_g = c_inf['geometry']
            if 'es_pico' not in c_inf:
                c_inf['es_pico'] = es_pico_real(c_g, c_inf['elevation'], idx, curvas_d, r=250)
            
            es_p = c_inf['es_pico']
            
            if es_p:
                centro = obtener_centro_curva(c_g)
                d_c = pt_act.distance(centro)
                d_p = c_g.distance(QgsGeometry.fromPointXY(pt_act))
                
                if d_p <= radio:
                    usar_p = d_c <= radio
                    d_rel = d_c if usar_p else d_p
                    cands.append({
                        'idx': fid, 'info': c_inf, 'dist': d_rel,
                        'es_pico': usar_p, 'pt_con': centro if usar_p else None, 'elev': e_obj
                    })
            else:
                d = c_g.distance(QgsGeometry.fromPointXY(pt_act))
                if d <= radio:
                    cands.append({
                        'idx': fid, 'info': c_inf, 'dist': d,
                        'es_pico': False, 'pt_con': None, 'elev': e_obj
                    })
        
        # Si encontró candidatas en esta elevación, retornar la mejor
        if cands:
            cands.sort(key=lambda x: (x['dist'], not x['es_pico']))
            return cands[0]
    
    return None


def verif_cruce_otra(pt_act, pt_nvo, otra_pts):
    if not otra_pts or len(otra_pts) < 2:
        return False, None
    seg = QgsGeometry.fromPolylineXY([pt_act, pt_nvo])
    g_otra = QgsGeometry.fromPolylineXY(otra_pts)
    if not seg.intersects(g_otra):
        return False, None
    inter = seg.intersection(g_otra)
    if inter.isEmpty():
        return False, None
    if inter.type() == QgsWkbTypes.PointGeometry:
        p = inter.asMultiPoint()[0] if inter.isMultipart() else inter.asPoint()
        return True, QgsPointXY(p)
    ctx = g_otra.closestSegmentWithContext(pt_nvo)
    return True, QgsPointXY(ctx[1])


def verif_autocruce(pts, pt_nvo):
    if len(pts) < 2:
        return False, None
    seg = QgsGeometry.fromPolylineXY([pts[-1], pt_nvo])
    prev = QgsGeometry.fromPolylineXY(pts[:-1])
    if prev.isEmpty() or not seg.intersects(prev):
        return False, None
    inter = seg.intersection(prev)
    if inter.isEmpty():
        return False, None
    if inter.type() == QgsWkbTypes.PointGeometry:
        p = inter.asMultiPoint()[0] if inter.isMultipart() else inter.asPoint()
        return True, QgsPointXY(p)
    ctx = prev.closestSegmentWithContext(pts[-1])
    return True, QgsPointXY(ctx[1])


def procesar_divisoria_individual(pt_ini, idx, curvas_d, num, pts_aux, otra_pts):
    bbox_ini = QgsRectangle(pt_ini.x()-25, pt_ini.y()-25, pt_ini.x()+25, pt_ini.y()+25)
    ids = idx.intersects(bbox_ini)
    
    d_min = float('inf')
    for fid in ids:
        d = curvas_d[fid]['geometry'].distance(QgsGeometry.fromPointXY(pt_ini))
        if d < d_min:
            d_min = d
    
    TOL = 5.0
    cands = []
    for fid in ids:
        d = curvas_d[fid]['geometry'].distance(QgsGeometry.fromPointXY(pt_ini))
        if d <= d_min + TOL:
            cands.append({'fid': fid, 'elev': curvas_d[fid]['elevation'], 'dist': d})
    
    if not cands:
        return {
            'puntos': [pt_ini], 'numero': num, 'elev_inicial': 0, 'elev_final': 0,
            'ganancia': 0, 'longitud': 0, 'num_puntos': 1, 'num_curvas': 0,
            'picos': 0, 'iteraciones': 0, 'razon': 'sin_elev_ini',
            'punto_final': pt_ini, 'curvas_usadas': set(), 'salto_auxiliar': False
        }
    
    cands.sort(key=lambda x: x['dist'])
    c_cerc = cands[0]
    
    if len(cands) >= 2:
        e_min_dos = min(c['elev'] for c in cands[:2])
    else:
        e_min_dos = c_cerc['elev']
    
    elev_ini = e_min_dos + 1 if c_cerc['elev'] == e_min_dos else c_cerc['elev']
    
    R_BASE = 50.0
    MULT = 5.0
    VENT = 5
    MAX_IT = 2000
    SEGS_LIB = 3
    
    pts = [pt_ini]
    pt_act = pt_ini
    elev_act = elev_ini
    curvas_u = set()
    picos = 0
    d_ult_seg = R_BASE
    it = 0
    pt_ant = pt_ini
    razon = "max_iter"
    
    while it < MAX_IT:
        it += 1
        r_busq = max(d_ult_seg * MULT, R_BASE)
        
        pts_rec = pts[-VENT:] if len(pts) >= VENT else pts
        dir_gen = calc_dir(pts_rec[0], pts_rec[-1]) if len(pts_rec) >= 2 else None
        
        mejor = buscar_curva(pt_act, idx, curvas_d, curvas_u, elev_act, r_busq, dir_gen)
        
        if mejor is None:
            razon = "sin_curvas"
            break
        
        idx_c = mejor['idx']
        c_inf = mejor['info']
        es_p = mejor['es_pico']
        verif_c = (it > SEGS_LIB)
        
        if es_p:
            picos += 1
            centro = mejor['pt_con']
            
            hay_c, p_c = verif_cruce_otra(pt_act, centro, otra_pts)
            if hay_c:
                pts.append(p_c)
                razon = "cruce_otra"
                break
            
            hay_a, p_a = verif_autocruce(pts, centro)
            if hay_a:
                pts.append(p_a)
                razon = "autocruce"
                break
            
            if verif_c:
                n_c, _ = contar_cruces(pt_ant, centro, idx, curvas_d, curvas_u, elev_act)
                if n_c >= 3:
                    razon = f"cruza_{n_c}"
                    break
            
            d_ult_seg = pt_act.distance(centro)
            pts.append(centro)
            pt_ant = pt_act
            pt_act = centro
            
            bbox_sig = QgsRectangle(centro.x()-r_busq*2, centro.y()-r_busq*2, centro.x()+r_busq*2, centro.y()+r_busq*2)
            ids_sig = idx.intersects(bbox_sig)
            c_sig = []
            for fid in ids_sig:
                if fid in curvas_u or fid == idx_c:
                    continue
                c = curvas_d[fid]
                if c['geometry'].distance(QgsGeometry.fromPointXY(centro)) <= r_busq * 2:
                    c_sig.append(c)
            
            pt_sal = pto_salida_cresta(centro, c_inf['geometry'], c_inf['elevation'], dir_gen, idx, curvas_d, c_sig)
            
            hay_c, p_c = verif_cruce_otra(centro, pt_sal, otra_pts)
            if hay_c:
                pts.append(p_c)
                razon = "cruce_sal_pico"
                break
            
            hay_a, p_a = verif_autocruce(pts, pt_sal)
            if hay_a:
                pts.append(p_a)
                razon = "autocruce_sal"
                break
            
            if verif_c:
                n_c_s, _ = contar_cruces(centro, pt_sal, idx, curvas_d, curvas_u, elev_act)
                if n_c_s >= 3:
                    razon = f"sal_pico_cruza_{n_c_s}"
                    break
            
            d_ult_seg = centro.distance(pt_sal)
            pts.append(pt_sal)
            pt_ant = centro
            pt_act = pt_sal
        else:
            res = c_inf['geometry'].closestSegmentWithContext(pt_act)
            pt_cerc = res[1]
            
            hay_c, p_c = verif_cruce_otra(pt_act, pt_cerc, otra_pts)
            if hay_c:
                pts.append(p_c)
                razon = "cruce_otra"
                break
            
            hay_a, p_a = verif_autocruce(pts, pt_cerc)
            if hay_a:
                pts.append(p_a)
                razon = "autocruce"
                break
            
            if verif_c:
                n_c, _ = contar_cruces(pt_ant, pt_cerc, idx, curvas_d, curvas_u, elev_act)
                if n_c >= 3:
                    razon = f"cruza_{n_c}"
                    break
            
            d_ult_seg = pt_act.distance(pt_cerc)
            pts.append(pt_cerc)
            pt_ant = pt_act
            pt_act = pt_cerc
        
        elev_act = c_inf['elevation']
        curvas_u.add(idx_c)
    
    long = QgsGeometry.fromPolylineXY(pts).length() if len(pts) >= 2 else 0
    gan = elev_act - elev_ini
    
    return {
        'puntos': pts, 'numero': num, 'elev_inicial': elev_ini, 'elev_final': elev_act,
        'ganancia': gan, 'longitud': long, 'num_puntos': len(pts), 'num_curvas': len(curvas_u),
        'picos': picos, 'iteraciones': it, 'razon': razon, 'punto_final': pt_act,
        'curvas_usadas': curvas_u, 'salto_auxiliar': False
    }


def procesar_desde_auxiliar(pt_aux, idx, curvas_d, elev_act_heredada, curvas_u_prev, otra_pts):
    """
    Procesa delimitación desde un punto auxiliar.
    Calcula elevación analizando terreno local, igual que puntos iniciales.
    """
    
    # Calcular elevación local del auxiliar
    bbox_aux = QgsRectangle(pt_aux.x()-25, pt_aux.y()-25, pt_aux.x()+25, pt_aux.y()+25)
    ids_cercanos = idx.intersects(bbox_aux)
    
    # Encontrar la curva más cercana
    d_min = float('inf')
    for fid in ids_cercanos:
        if fid in curvas_u_prev:
            continue
        d = curvas_d[fid]['geometry'].distance(QgsGeometry.fromPointXY(pt_aux))
        if d < d_min:
            d_min = d
    
    # Buscar candidatas dentro de tolerancia
    TOL = 5.0
    cands = []
    for fid in ids_cercanos:
        if fid in curvas_u_prev:
            continue
        d = curvas_d[fid]['geometry'].distance(QgsGeometry.fromPointXY(pt_aux))
        if d <= d_min + TOL:
            cands.append({'fid': fid, 'elev': curvas_d[fid]['elevation'], 'dist': d})
    
    if not cands:
        # Fallback: usar elevación heredada si no hay curvas cercanas
        elev_inicial = elev_act_heredada
    else:
        # Aplicar misma metodología que puntos iniciales
        cands.sort(key=lambda x: x['dist'])
        c_cerc = cands[0]
        
        if len(cands) >= 2:
            e_min_dos = min(c['elev'] for c in cands[:2])
        else:
            e_min_dos = c_cerc['elev']
        
        # Si está en la curva menor, sube +1
        elev_inicial = e_min_dos + 1 if c_cerc['elev'] == e_min_dos else c_cerc['elev']
    
    R_BASE = 50.0
    MULT = 5.0
    VENT = 5
    MAX_IT = 1000
    SEGS_LIB = 5
    
    pts = [pt_aux]
    pt_act = pt_aux
    curvas_u = set(curvas_u_prev)
    picos = 0
    d_ult = R_BASE
    it = 0
    pt_ant = pt_aux
    razon = "max_iter"
    elev_act = elev_inicial
    
    while it < MAX_IT:
        it += 1
        r_busq = max(d_ult * MULT, R_BASE)
        
        pts_rec = pts[-VENT:] if len(pts) >= VENT else pts
        dir_gen = calc_dir(pts_rec[0], pts_rec[-1]) if len(pts_rec) >= 2 else None
        
        mejor = buscar_curva(pt_act, idx, curvas_d, curvas_u, elev_act, r_busq, dir_gen)
        
        if mejor is None:
            razon = "sin_curvas"
            break
        
        idx_c = mejor['idx']
        c_inf = mejor['info']
        es_p = mejor['es_pico']
        verif_c = (it > SEGS_LIB)
        
        if es_p:
            picos += 1
            centro = mejor['pt_con']
            
            hay_c, p_c = verif_cruce_otra(pt_act, centro, otra_pts)
            if hay_c:
                pts.append(p_c)
                razon = "cruce_otra"
                break
            
            if verif_c:
                n_c, _ = contar_cruces(pt_ant, centro, idx, curvas_d, curvas_u, elev_act)
                if n_c >= 3:
                    razon = f"cruza_{n_c}"
                    break
            
            d_ult = pt_act.distance(centro)
            pts.append(centro)
            pt_ant = pt_act
            pt_act = centro
            
            bbox_sig = QgsRectangle(centro.x()-r_busq*2, centro.y()-r_busq*2, centro.x()+r_busq*2, centro.y()+r_busq*2)
            ids_sig = idx.intersects(bbox_sig)
            c_sig = []
            for fid in ids_sig:
                if fid in curvas_u or fid == idx_c:
                    continue
                c = curvas_d[fid]
                if c['geometry'].distance(QgsGeometry.fromPointXY(centro)) <= r_busq * 2:
                    c_sig.append(c)
            
            pt_sal = pto_salida_cresta(centro, c_inf['geometry'], c_inf['elevation'], dir_gen, idx, curvas_d, c_sig)
            
            hay_c, p_c = verif_cruce_otra(centro, pt_sal, otra_pts)
            if hay_c:
                pts.append(p_c)
                razon = "cruce_sal"
                break
            
            if verif_c:
                n_c_s, _ = contar_cruces(centro, pt_sal, idx, curvas_d, curvas_u, elev_act)
                if n_c_s >= 3:
                    razon = f"sal_cruza_{n_c_s}"
                    break
            
            d_ult = centro.distance(pt_sal)
            pts.append(pt_sal)
            pt_ant = centro
            pt_act = pt_sal
        else:
            res = c_inf['geometry'].closestSegmentWithContext(pt_act)
            pt_cerc = res[1]
            
            hay_c, p_c = verif_cruce_otra(pt_act, pt_cerc, otra_pts)
            if hay_c:
                pts.append(p_c)
                razon = "cruce_otra"
                break
            
            if verif_c:
                n_c, _ = contar_cruces(pt_ant, pt_cerc, idx, curvas_d, curvas_u, elev_act)
                if n_c >= 3:
                    razon = f"cruza_{n_c}"
                    break
            
            d_ult = pt_act.distance(pt_cerc)
            pts.append(pt_cerc)
            pt_ant = pt_act
            pt_act = pt_cerc
        
        elev_act = c_inf['elevation']
        curvas_u.add(idx_c)
    
    return {
        'puntos': pts, 
        'elev_inicial': elev_inicial,
        'elev_final': elev_act, 
        'iteraciones': it, 
        'razon': razon
    }

def recortar_lineas_en_cruce(pts1, pts2):
    """
    Detecta el primer cruce entre dos líneas y las recorta hasta ese punto.
    Retorna las líneas recortadas y el punto de cruce.
    """
    if len(pts1) < 2 or len(pts2) < 2:
        return pts1, pts2, None
    
    # Buscar todos los cruces posibles
    cruces = []
    
    for i in range(len(pts1) - 1):
        seg1 = QgsGeometry.fromPolylineXY([pts1[i], pts1[i+1]])
        
        for j in range(len(pts2) - 1):
            seg2 = QgsGeometry.fromPolylineXY([pts2[j], pts2[j+1]])
            
            if seg1.intersects(seg2):
                inter = seg1.intersection(seg2)
                if not inter.isEmpty() and inter.type() == QgsWkbTypes.PointGeometry:
                    p_cruce = inter.asMultiPoint()[0] if inter.isMultipart() else inter.asPoint()
                    pt_cruce = QgsPointXY(p_cruce)
                    
                    # Calcular distancia desde el inicio de cada línea
                    dist1 = sum(pts1[k].distance(pts1[k+1]) for k in range(i))
                    dist1 += pts1[i].distance(pt_cruce)
                    
                    dist2 = sum(pts2[k].distance(pts2[k+1]) for k in range(j))
                    dist2 += pts2[j].distance(pt_cruce)
                    
                    cruces.append({
                        'punto': pt_cruce,
                        'idx1': i,
                        'idx2': j,
                        'dist_total': dist1 + dist2
                    })
    
    if not cruces:
        return pts1, pts2, None
    
    # Tomar el cruce más cercano al inicio (menor distancia total)
    cruce = min(cruces, key=lambda x: x['dist_total'])
    pt_cruce = cruce['punto']
    idx1 = cruce['idx1']
    idx2 = cruce['idx2']
    
    # Recortar línea 1 hasta el cruce
    pts1_recortada = pts1[:idx1+1]
    pts1_recortada.append(pt_cruce)
    
    # Recortar línea 2 hasta el cruce
    pts2_recortada = pts2[:idx2+1]
    pts2_recortada.append(pt_cruce)
    
    return pts1_recortada, pts2_recortada, pt_cruce


def crear_poligono_cuenca(pts1, pts2):
    if len(pts1) < 2 or len(pts2) < 2:
        return None
    
    poly_pts = []
    poly_pts.extend(pts1)
    poly_pts.extend(list(reversed(pts2)))
    
    if len(poly_pts) < 3:
        return None
    
    try:
        poly_g = QgsGeometry.fromPolygonXY([poly_pts])
        if poly_g.isEmpty():
            return None
        if not poly_g.isGeosValid():
            poly_g = poly_g.makeValid()
            if poly_g.isEmpty():
                return None
        return poly_g
    except:
        return None