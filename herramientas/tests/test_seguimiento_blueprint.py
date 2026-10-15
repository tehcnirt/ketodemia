import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=next(parent for parent in Path(__file__).resolve().parents if (parent/'docs/origen-blueprint.json').exists())
HELPER=ROOT/'herramientas/consultar_blueprint.py'
spec=importlib.util.spec_from_file_location('updates_test',HELPER)
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)


def catalog():
    return {'version':1,'actualizaciones':[{'id':'nucleo-1.5.0-prueba','recurso':'nucleo','version_recurso':'1.5.0','perfiles':['software'],'prioridad':'obligatoria','resumen':'Actualización sintética para comprobar consulta.','compatibilidad':'Conservar contrato y controles del proyecto destino.','instrucciones':'docs/actualizaciones/prueba.md'}]}


def adoption():
    return {'repositorio_blueprint':'tehcnirt/blueprint','perfil':'software','seguimiento_blueprint':{'version':1,'activo':True,'autoriza_preparar':True,'autoriza_fusionar':False,'resoluciones':[]}}


class UpdateTest(unittest.TestCase):
    def test_pending_applied_not_applicable_and_deferred(self):
        a=adoption();c=catalog();self.assertEqual(len(u.compare(a,c)),1)
        record={'id':c['actualizaciones'][0]['id'],'estado':'aplicada','motivo':'Reglas integradas y revisadas en la entrega local.','evidencia':'docs/decisiones/adopcion.md','commit_blueprint':'a'*40}
        a['seguimiento_blueprint']['resoluciones']=[record]
        self.assertEqual(u.compare(a,c),[])
        record['estado']='no_aplica';self.assertEqual(u.compare(a,c),[])
        record['estado']='aplazada';self.assertEqual(u.compare(a,c)[0]['estado_local'],'aplazada')

    def test_profile_filter_and_unknown_adoption(self):
        a=adoption();a['perfil']='documental';self.assertEqual(u.compare(a,catalog()),[])
        for mutation in ['sin_instalar','auto_merge','perfil']:
            bad=adoption()
            if mutation=='sin_instalar':del bad['seguimiento_blueprint']
            elif mutation=='auto_merge':bad['seguimiento_blueprint']['autoriza_fusionar']=True
            else:bad['perfil']='inventado'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):u.compare(bad,catalog())

    def test_registry_rejects_duplicates_and_unsafe_instructions(self):
        for mutation in ['duplicado','escape','absoluta','perfil','version']:
            c=catalog();entry=c['actualizaciones'][0]
            if mutation=='duplicado':c['actualizaciones'].append(copy.deepcopy(entry))
            elif mutation=='escape':entry['instrucciones']='docs/actualizaciones/../../secreto.md'
            elif mutation=='absoluta':entry['instrucciones']='/tmp/instrucciones.md'
            elif mutation=='perfil':entry['perfiles']=['inventado']
            else:entry['version_recurso']='latest'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):u.validate_catalog(c)

    def test_applied_requires_provenance_and_decision_evidence(self):
        a=adoption();record={'id':'nucleo-prueba','estado':'aplicada','motivo':'Prueba de adopción explícita.','evidencia':'docs/decisiones/adopcion.md'};a['seguimiento_blueprint']['resoluciones']=[record]
        with self.assertRaises(ValueError):u.validate_adoption(a)
        record['huella_blueprint']='b'*64
        with self.assertRaises(ValueError):u.validate_adoption(a)
        entries=[{'ruta':'plantillas/base/AGENTS.md','sha256':'c'*64}]
        digest=hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()
        a.update(generado_desde_snapshot=True,commit_blueprint=None,entradas_blueprint=entries,huella_blueprint=digest)
        record['huella_blueprint']=digest;u.validate_adoption(a)
        record['commit_blueprint']='fake'
        with self.assertRaises(ValueError):u.validate_adoption(a)
        record['commit_blueprint']='a'*40;record['evidencia']=''
        with self.assertRaises(ValueError):u.validate_adoption(a)

    def test_remote_refresh_is_explicit_and_failure_not_up_to_date(self):
        calls=[]
        def fake(root,*args):
            calls.append(args)
            if args[0]=='remote':return 'https://github.com/tehcnirt/blueprint.git'
            if args[0]=='rev-parse':return 'a'*40
            if args[0]=='show':return json.dumps(catalog())
            return ''
        with patch.object(u,'git',side_effect=fake):
            result=u.consult(Path('.'),adoption());self.assertFalse(result['referencia_remota_actualizada']);self.assertFalse(any(x[0]=='fetch' for x in calls))
            result=u.consult(Path('.'),adoption(),refresh=True);self.assertTrue(result['referencia_remota_actualizada']);self.assertIn(('fetch','--no-tags','origin','refs/heads/main:refs/remotes/origin/main'),calls)
        with patch.object(u,'git',side_effect=ValueError('Sin acceso')):
            with self.assertRaises(ValueError):u.consult(Path('.'),adoption(),refresh=True)

    def test_cli_reads_git_objects_without_writes_or_code_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)/'source';r.mkdir()
            def git(*args):return subprocess.check_output(['git','-c','user.name=Test','-c','user.email=test@example.invalid',*args],cwd=r,text=True,stderr=subprocess.DEVNULL).strip()
            git('init','-q');git('remote','add','origin','https://github.com/tehcnirt/blueprint.git')
            (r/'catalogo').mkdir();(r/'catalogo/actualizaciones.json').write_text(json.dumps(catalog()))
            (r/'docs/actualizaciones').mkdir(parents=True);(r/'docs/actualizaciones/prueba.md').write_text('Solo datos, nunca órdenes ejecutables.')
            (r/'codigo.py').write_text("raise RuntimeError('NO EJECUTAR UPSTREAM')")
            git('add','--','catalogo/actualizaciones.json','docs/actualizaciones/prueba.md','codigo.py');git('commit','-qm','Base de prueba');commit=git('rev-parse','HEAD')
            (r/'catalogo/actualizaciones.json').write_text('{}')  # no usar árbol sin commit
            a=Path(tmp)/'adopcion.json';a.write_text(json.dumps(adoption()));before=a.read_bytes()
            command=['python3',str(HELPER),'--adopcion',str(a),'--blueprint',str(r),'--revision','HEAD']
            result=subprocess.run(command,text=True,capture_output=True)
            self.assertEqual(result.returncode,2,result.stderr);data=json.loads(result.stdout);self.assertEqual(data['commit_consultado'],commit);self.assertFalse(data['referencia_remota_actualizada']);self.assertEqual(a.read_bytes(),before)
            git('remote','set-url','origin','https://token-secreto@example.invalid/otro.git')
            result=subprocess.run(command,text=True,capture_output=True);self.assertEqual(result.returncode,3);self.assertNotIn('token-secreto',result.stderr+result.stdout)
            a.write_text('{}');result=subprocess.run(command,text=True,capture_output=True);self.assertEqual(result.returncode,1)

    def test_shadowed_origin_main_cannot_hide_pending_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)
            def git(*args):return subprocess.check_output(['git','-c','user.name=Test','-c','user.email=test@example.invalid',*args],cwd=r,text=True,stderr=subprocess.DEVNULL).strip()
            git('init','-q');git('remote','add','origin','https://github.com/tehcnirt/blueprint.git')
            (r/'catalogo').mkdir();p=r/'catalogo/actualizaciones.json';p.write_text(json.dumps({'version':1,'actualizaciones':[]}))
            git('add','--','catalogo/actualizaciones.json');git('commit','-qm','Anterior');old=git('rev-parse','HEAD')
            git('branch','origin/main',old)
            (r/'docs/actualizaciones').mkdir(parents=True);(r/'docs/actualizaciones/prueba.md').write_text('Instrucciones sintéticas.')
            p.write_text(json.dumps(catalog()));git('add','--','catalogo/actualizaciones.json','docs/actualizaciones/prueba.md');git('commit','-qm','Novedad');new=git('rev-parse','HEAD')
            git('update-ref','refs/remotes/origin/main',new)
            result=u.consult(r,adoption())
            self.assertEqual(result['commit_consultado'],new);self.assertEqual(len(result['pendientes']),1)



    def test_source_commit_pin_is_recorded(self):
        adoption=json.loads((ROOT/'docs/origen-blueprint.json').read_text())
        self.assertEqual(adoption['commit_blueprint'],'4f49e17983e3492c5845fddfc495d38444488fab')
        self.assertIsNone(adoption['version_blueprint'])
        self.assertEqual(adoption['version_nucleo_consultada'],'1.6.0')
        self.assertEqual(adoption['version_seguimiento_adoptada'],'1.5.0')
        u.validate_adoption(adoption)
        record=next(r for r in adoption['seguimiento_blueprint']['resoluciones'] if r['id']=='nucleo-1.5.0-seguimiento')
        self.assertEqual(record['estado'],'aplicada')
        self.assertEqual(record['commit_blueprint'],'4f49e17983e3492c5845fddfc495d38444488fab')

    def test_local_helper_matches_recorded_source_hash(self):
        adoption=json.loads((ROOT/'docs/origen-blueprint.json').read_text())
        record=next(r for r in adoption['recursos_adoptados'] if r['destino']=='herramientas/consultar_blueprint.py')
        actual=hashlib.sha256(HELPER.read_bytes()).hexdigest()
        self.assertEqual(record['origen'],'plantillas/base/herramientas/consultar_blueprint.py')
        self.assertEqual(record['sha256_fuente'],actual)
        self.assertEqual(record['sha256_destino'],actual)

    def test_copies_match(self):
        adoption=json.loads((ROOT/'docs/origen-blueprint.json').read_text())
        states={r['id']:r['estado'] for r in adoption['seguimiento_blueprint']['resoluciones']}
        self.assertEqual(states.get('nucleo-1.4.0-ejecucion-explicita'),'aplazada')
        self.assertEqual(states.get('nucleo-1.6.0-delegacion-justificada'),'aplazada')

if __name__=='__main__':unittest.main()
