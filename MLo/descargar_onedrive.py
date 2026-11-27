"""Descarga local de PNG compartidos en un correo EML mediante OneDrive.
No contiene enlaces privados ni credenciales. Requiere permiso de descarga.
"""
import argparse
import csv
import hashlib
import re
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DOWNLOAD = re.compile(r'^(descargar|download)( archivo| file)?$', re.I)
MORE = re.compile(r'^(más|más acciones|más opciones|more|more actions|more options)$', re.I)


def extract(eml):
    with eml.open('rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    body = msg.get_body(preferencelist=('html',))
    if not body:
        raise ValueError('El correo no contiene HTML.')
    soup = BeautifulSoup(body.get_content(), 'html.parser')
    result, seen, names = [], set(), set()
    for a in soup.find_all('a', href=True):
        url = a['href']
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname != '1drv.ms' or url in seen:
            continue
        name = a.get_text(strip=True)
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.png', name, re.I):
            continue
        if name in names:
            raise ValueError(f'Nombre repetido: {name}')
        result.append((name, url))
        seen.add(url)
        names.add(name)
    return result


def inspect_png(path):
    with Image.open(path) as im:
        if im.format != 'PNG':
            raise ValueError('El archivo no es PNG.')
        width, height = im.size
        im.verify()
    return width, height, hashlib.sha256(path.read_bytes()).hexdigest()


def candidates(page, pattern):
    return [page.get_by_role('button', name=pattern),
            page.get_by_role('menuitem', name=pattern),
            page.get_by_role('link', name=pattern),
            page.get_by_text(pattern, exact=True)]


def visible_button(page, pattern):
    for group in candidates(page, pattern):
        for i in range(min(group.count(), 12)):
            loc = group.nth(i)
            if loc.is_visible():
                return loc
    return None


def open_link(page, url):
    page.goto(url, wait_until='domcontentloaded', timeout=45000)


def save_one(page, url, dest):
    open_link(page, url)
    button = None
    # OneDrive can render the action asynchronously.
    for _ in range(20):
        button = visible_button(page, DOWNLOAD)
        if button is not None:
            break
        page.wait_for_timeout(500)
    if button is None:
        more = visible_button(page, MORE)
        if more is not None:
            more.click(timeout=5000)
            page.wait_for_timeout(800)
            button = visible_button(page, DOWNLOAD)
    if button is None:
        raise RuntimeError('No se encontró Descargar (revisar sesión/permisos/interfaz).')
    with page.expect_download(timeout=45000) as info:
        button.click(timeout=10000)
    tmp = dest.with_suffix('.png.part')
    try:
        info.value.save_as(tmp)
        inspect_png(tmp)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eml', type=Path)
    parser.add_argument('--output', type=Path, default=Path('dataset/raw'))
    parser.add_argument('--limit', type=int, default=0, help='0 = todos; 1 = prueba inicial')
    parser.add_argument('--list', action='store_true', help='Solo contar; no abre el navegador')
    args = parser.parse_args()
    if args.limit < 0:
        parser.error('--limit debe ser positivo o 0')
    rows = extract(args.eml)
    print(f'{len(rows)} enlaces PNG únicos encontrados.')
    if args.list or not rows:
        return
    if args.limit:
        rows = rows[:args.limit]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = out.parent / 'descargas.csv'
    # Existing valid files are not downloaded again. Hashes flag duplicates.
    hashes = {}
    for p in out.glob('*.png'):
        try:
            _, _, h = inspect_png(p)
            hashes.setdefault(h, p.name)
        except Exception:
            pass
    success = failures = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        try:
            open_link(page, rows[0][1])
        except Exception:
            print('No se pudo abrir el primer enlace automáticamente.')
        print('Inicia sesión en Microsoft si hace falta y comprueba que aparece la imagen y Descargar.')
        input('Cuando tengas acceso, presiona Enter aquí para continuar... ')
        with report.open('a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['archivo','estado','ancho','alto','sha256','duplicado_de','detalle'])
            consecutive = 0
            for i, (name, url) in enumerate(rows, 1):
                dest = out / name
                try:
                    state = 'existente'
                    try:
                        w, h, digest = inspect_png(dest)
                    except Exception:
                        save_one(page, url, dest)
                        w, h, digest = inspect_png(dest)
                        state = 'descargado'
                    previous = hashes.get(digest, '')
                    duplicate = previous if previous != name else ''
                    hashes.setdefault(digest, name)
                    writer.writerow([name,state,w,h,digest,duplicate,''])
                    success += 1
                    consecutive = 0
                    print(f'[{i}/{len(rows)}] OK {name} ({w}x{h})')
                except Exception as exc:
                    # Do not print exception text: it may contain a private URL.
                    detail = type(exc).__name__
                    if isinstance(exc, RuntimeError):
                        detail = 'No se encontró el botón Descargar.'
                    writer.writerow([name,'fallo','','','','',detail])
                    failures += 1
                    consecutive += 1
                    print(f'[{i}/{len(rows)}] Fallo {name}: {detail}')
                f.flush()
                if consecutive >= 3:
                    print('Tres fallos seguidos. Revisa permisos o sesión y ejecuta de nuevo; se omitirán los archivos válidos.')
                    break
                page.wait_for_timeout(400)
        browser.close()
    print(f'Correctos: {success}; fallidos: {failures}; pendientes sin intentar: {len(rows)-success-failures}')
    print(f'Reporte: {report}')


if __name__ == '__main__':
    main()
