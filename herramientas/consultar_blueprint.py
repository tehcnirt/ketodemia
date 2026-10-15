#!/usr/bin/env python3
"""Consulta actualizaciones como datos; nunca copia archivos ni ejecuta código upstream."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPOSITORY = 'tehcnirt/blueprint'
REMOTES = {'https://github.com/tehcnirt/blueprint.git', 'https://github.com/tehcnirt/blueprint', 'git@github.com:tehcnirt/blueprint.git'}
PROFILES = {'documental', 'software', 'infraestructura'}
SHA = re.compile(r'[0-9a-f]{40}')


def safe_path(value):
    if not isinstance(value, str) or not value:
        raise ValueError('Ruta ausente.')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or '\\' in value:
        raise ValueError('Ruta no portable.')
    return path


def validate_catalog(value):
    if not isinstance(value, dict) or type(value.get('version')) is not int or value.get('version') != 1 or not isinstance(value.get('actualizaciones'), list):
        raise ValueError('Índice de actualizaciones inválido.')
    ids = set()
    for update in value['actualizaciones']:
        if not isinstance(update, dict):
            raise ValueError('Actualización inválida.')
        identifier = update.get('id', '')
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]+', identifier) or identifier in ids:
            raise ValueError('ID inválido o duplicado.')
        ids.add(identifier)
        if update.get('recurso') != 'nucleo' or not re.fullmatch(r'\d+\.\d+\.\d+', update.get('version_recurso', '')):
            raise ValueError('Recurso/versión de actualización no válidos.')
        profiles = update.get('perfiles')
        if not isinstance(profiles, list) or not profiles or not set(profiles) <= PROFILES:
            raise ValueError('Perfiles de actualización inválidos.')
        if update.get('prioridad') not in {'obligatoria', 'recomendada'}:
            raise ValueError('Prioridad inválida.')
        note = safe_path(update.get('instrucciones'))
        if note.parts[:2] != ('docs', 'actualizaciones') or note.suffix != '.md':
            raise ValueError('Instrucciones fuera de docs/actualizaciones.')
        for key in ['resumen', 'compatibilidad']:
            if not isinstance(update.get(key), str) or len(update[key].strip()) < 10:
                raise ValueError('Descripción de actualización incompleta.')
    return value


def validate_adoption(value):
    if not isinstance(value, dict) or value.get('repositorio_blueprint') != REPOSITORY or value.get('perfil') not in PROFILES:
        raise ValueError('Procedencia o perfil local inválidos.')
    tracking = value.get('seguimiento_blueprint')
    if not isinstance(tracking, dict) or tracking.get('version') != 1 or tracking.get('activo') is not True:
        raise ValueError('Seguimiento sin instalar o desactivado; requiere adopción explícita.')
    if tracking.get('autoriza_preparar') is not True or tracking.get('autoriza_fusionar') is not False:
        raise ValueError('Autorización inválida: preparar sí; fusionar no.')
    records = tracking.get('resoluciones')
    if not isinstance(records, list):
        raise ValueError('Faltan resoluciones locales.')
    ids = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('id'), str) or record['id'] in ids:
            raise ValueError('Resolución duplicada o inválida.')
        ids.add(record['id'])
        if record.get('estado') not in {'aplicada', 'no_aplica', 'aplazada'}:
            raise ValueError('Estado de adopción inválido.')
        for key in ['motivo', 'evidencia']:
            if not isinstance(record.get(key), str) or len(record[key].strip()) < 8:
                raise ValueError('Resolución sin motivo/evidencia.')
        if record['estado'] == 'aplicada':
            commit = record.get('commit_blueprint')
            if commit is not None:
                if not isinstance(commit, str) or not SHA.fullmatch(commit):
                    raise ValueError('Adopción aplicada con commit fuente inválido.')
            else:
                entries = value.get('entradas_blueprint')
                snapshot = (value.get('generado_desde_snapshot') is True
                            and 'commit_blueprint' in value and value['commit_blueprint'] is None
                            and isinstance(entries, list) and bool(entries))
                if not snapshot:
                    raise ValueError('Huella sin commit reservada a generación desde snapshot documentado.')
                for entry in entries:
                    if not isinstance(entry, dict) or not re.fullmatch(r'[0-9a-f]{64}', entry.get('sha256', '')):
                        raise ValueError('Manifiesto snapshot inválido.')
                    safe_path(entry.get('ruta'))
                digest = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
                if record.get('huella_blueprint') != digest or value.get('huella_blueprint') != digest:
                    raise ValueError('Huella snapshot no corresponde al manifiesto de origen.')
    return tracking


def compare(adoption, catalog):
    tracking = validate_adoption(adoption)
    validate_catalog(catalog)
    records = {record['id']: record for record in tracking['resoluciones']}
    pending = []
    for update in catalog['actualizaciones']:
        if adoption['perfil'] not in update['perfiles']:
            continue
        record = records.get(update['id'])
        if record is None or record['estado'] == 'aplazada':
            pending.append(dict(update, estado_local=record['estado'] if record else 'sin_revisar'))
    return pending


def git(root, *args):
    process = subprocess.run(['git', '-C', str(root), *args], text=True, capture_output=True)
    if process.returncode:
        raise ValueError('No se pudo consultar Git; referencia/acceso no verificados.')
    return process.stdout.strip()


def consult(root, adoption, revision='origin/main', refresh=False):
    if git(root, 'remote', 'get-url', 'origin') not in REMOTES:
        raise ValueError('El clon fuente no apunta al Blueprint autorizado.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]*', revision):
        raise ValueError('Referencia de consulta inválida.')
    if refresh:
        if revision != 'origin/main':
            raise ValueError('La consulta remota solo refresca origin/main.')
        git(root, 'fetch', '--no-tags', 'origin', 'refs/heads/main:refs/remotes/origin/main')
    canonical = 'refs/remotes/origin/main' if revision == 'origin/main' else revision
    commit = git(root, 'rev-parse', '--verify', canonical + '^{commit}')
    catalog = validate_catalog(json.loads(git(root, 'show', commit + ':catalogo/actualizaciones.json')))
    for update in catalog['actualizaciones']:
        git(root, 'cat-file', '-e', commit + ':' + update['instrucciones'])
    pending = compare(adoption, catalog)
    return {'version': 1, 'repositorio': REPOSITORY, 'commit_consultado': commit,
            'referencia_remota_actualizada': refresh, 'pendientes': pending,
            'resultado': 'actualizaciones_pendientes' if pending else 'sin_actualizaciones_pendientes',
            'limite': 'Consulta de datos; no acredita adopción real ni ejecuta instrucciones upstream.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adopcion', type=Path, default=Path('docs/origen-blueprint.json'))
    parser.add_argument('--blueprint', type=Path, required=True)
    parser.add_argument('--revision', default='origin/main')
    parser.add_argument('--consultar-remoto', action='store_true')
    args = parser.parse_args()
    try:
        adoption = json.loads(args.adopcion.read_text())
        validate_adoption(adoption)
    except (OSError, ValueError, TypeError, KeyError):
        print('Registro local inválido o seguimiento no instalado.', file=sys.stderr)
        return 1
    try:
        result = consult(args.blueprint, adoption, args.revision, args.consultar_remoto)
    except (OSError, ValueError, TypeError, KeyError):
        print('Fuente no verificada: no afirmar que está al día; declarar límite y revisar acceso/referencia.', file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['pendientes'] else 0


if __name__ == '__main__':
    sys.exit(main())
