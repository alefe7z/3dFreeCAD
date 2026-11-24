#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Package the ArtCAM importer as a FreeCAD user add-on (zip), from the sources in this branch.

Coordination tool (see artcam-handoff/README.md); not part of FreeCAD. The add-on lets an
installed FreeCAD 1.x open .art files without building this fork:

    python3 artcam-handoff/tools/build_addon.py [output.zip]

The zip holds one folder, ArtCAMImport/, to be extracted into the "Mod" folder inside the
directory returned by App.getUserAppDataDir() in FreeCAD's Python console.
"""

import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMPORT_DIR = os.path.join(ROOT, "src", "Mod", "Import")
SOURCES = ["importArtCAM.py", "artcam/__init__.py", "artcam/cfb.py", "artcam/reader.py"]

INIT_PY = '''# SPDX-License-Identifier: LGPL-2.1-or-later
"""Register the ArtCAM (.art) importer, unless this FreeCAD build already provides it."""

import FreeCAD

if "importArtCAM" not in FreeCAD.getImportType("art"):
    FreeCAD.addImportType("ArtCAM project toolpaths (*.art *.ART)", "importArtCAM")
'''

README_TXT = """ArtCAMImport - importador de arquivos ArtCAM (.art) para o FreeCAD 1.x

INSTALACAO
1. No FreeCAD, abra o Console Python (Exibir > Paineis > Console Python;
   em ingles: View > Panels > Python console) e digite:
       App.getUserAppDataDir()
   Anote a pasta exibida.
2. Dentro dessa pasta, abra (ou crie) a subpasta "Mod".
3. Extraia este zip dentro de "Mod". Deve ficar: Mod/ArtCAMImport/Init.py
4. Feche e abra o FreeCAD de novo.

USO
- Arquivo > Abrir (ou Arquivo > Importar) e escolha um arquivo .art.
  O tipo "ArtCAM project toolpaths (*.art *.ART)" aparece na lista de formatos.
- Cada percurso de usinagem vira um objeto (nome = nome do percurso), dentro de um grupo
  com o nome do arquivo. A propriedade "Tool" mostra a ferramenta.

LIMITACOES
- Os vetores de desenho do ArtCAM sao gravados cifrados e NAO sao importados.
  As linhas importadas sao as trajetorias do centro da ferramenta (percursos calculados).
  Num perfil, a linha fica deslocada do desenho pelo raio da ferramenta.
- Relevos 3D e profundidades (Z) ainda nao sao importados.
- Testado com arquivos do ArtCAM Pro 2008. Arquivos do 2013 ainda nao foram verificados.
- Mensagens e avisos aparecem no painel Visao de relatorio (View > Panels > Report view).
"""


def build(output):
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ArtCAMImport/Init.py", INIT_PY)
        archive.writestr("ArtCAMImport/LEIA-ME.txt", README_TXT)
        for source in SOURCES:
            archive.write(os.path.join(IMPORT_DIR, source), "ArtCAMImport/" + source)
    print(f"Add-on written: {output}")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "ArtCAMImport.zip")
