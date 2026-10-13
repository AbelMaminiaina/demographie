"""Calculs géométriques simples sur des contours GeoJSON (sans dépendance SIG)."""
import math


def anneaux(geometrie):
    """Contours extérieurs d'un Polygon ou MultiPolygon (les trous sont ignorés)."""
    polys = geometrie["coordinates"] if geometrie["type"] == "MultiPolygon" else [geometrie["coordinates"]]
    return [poly[0] for poly in polys]


def _aire_signee(xy):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(xy, xy[1:] + xy[:1])) / 2


def superficie_km2(geometrie):
    """Superficie approchée (projection équirectangulaire locale, formule du lacet)."""
    total = 0.0
    for anneau in anneaux(geometrie):
        lat0 = math.radians(sum(p[1] for p in anneau) / len(anneau))
        xy = [(p[0] * 111.32 * math.cos(lat0), p[1] * 110.57) for p in anneau]
        total += abs(_aire_signee(xy))
    return total


def point_interieur(geometrie):
    """Point garanti à l'intérieur du plus grand contour.

    On trace une horizontale à mi-hauteur et on prend le milieu du plus large segment
    intérieur : contrairement au centroïde, ce point ne tombe jamais hors d'une forme concave.
    """
    anneau = max(anneaux(geometrie), key=lambda a: abs(_aire_signee([(p[0], p[1]) for p in a])))
    ys = [p[1] for p in anneau]
    y = (min(ys) + max(ys)) / 2
    xs = sorted(
        x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        for (x1, y1, *_), (x2, y2, *_) in zip(anneau, anneau[1:] + anneau[:1])
        if (y1 > y) != (y2 > y)
    )
    segments = list(zip(xs[::2], xs[1::2]))
    debut, fin = max(segments, key=lambda s: s[1] - s[0])
    return (debut + fin) / 2, y


def contient(geometrie, point):
    """Test point-dans-polygone (règle pair-impair) sur les contours extérieurs."""
    x, y = point
    for anneau in anneaux(geometrie):
        dedans = False
        for (x1, y1, *_), (x2, y2, *_) in zip(anneau, anneau[1:] + anneau[:1]):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                dedans = not dedans
        if dedans:
            return True
    return False


def boite(geometrie):
    pts = [p for a in anneaux(geometrie) for p in a]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def _douglas_peucker(points, tolerance):
    """Simplification d'une ligne (algorithme de Douglas-Peucker, version itérative)."""
    garder = [False] * len(points)
    garder[0] = garder[-1] = True
    piles = [(0, len(points) - 1)]
    while piles:
        debut, fin = piles.pop()
        (x1, y1), (x2, y2) = points[debut], points[fin]
        dx, dy = x2 - x1, y2 - y1
        norme = math.hypot(dx, dy) or 1e-12
        indice, distance_max = None, tolerance
        for i in range(debut + 1, fin):
            x, y = points[i]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norme
            if d > distance_max:
                indice, distance_max = i, d
        if indice is not None:
            garder[indice] = True
            piles += [(debut, indice), (indice, fin)]
    return [p for p, g in zip(points, garder) if g]


def simplifier(geometrie, tolerance, decimales=3):
    """Contours extérieurs simplifiés et arrondis, au format MultiPolygon.

    Les anneaux devenus trop petits disparaissent ; on garde toujours le plus grand.
    """
    resultat = []
    for anneau in sorted(anneaux(geometrie), key=lambda a: -abs(_aire_signee([p[:2] for p in a]))):
        brut = [tuple(p[:2]) for p in anneau]
        # Un anneau fermé commence et finit au même point : on le simplifie en deux moitiés.
        milieu = len(brut) // 2
        pts = _douglas_peucker(brut[:milieu + 1], tolerance)[:-1] + _douglas_peucker(brut[milieu:], tolerance)
        pts = [(round(x, decimales), round(y, decimales)) for x, y in pts]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if len(pts) >= 4 or not resultat:
            resultat.append([[list(p) for p in pts]])
    return {"type": "MultiPolygon", "coordinates": resultat}
