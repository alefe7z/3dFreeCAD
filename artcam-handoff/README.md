# Handoff: importador ArtCAM (.art) para o FreeCAD

Documento de passagem de trabalho entre agentes de IA. Leia **inteiro** antes de mexer em qualquer
arquivo. Toda ação deve ser registrada em [LOG.md](LOG.md) (protocolo na seção 2).

> Esta pasta (`artcam-handoff/`) é material de coordenação. **Não faz parte da contribuição ao
> FreeCAD** e deve ser removida antes de qualquer PR para o upstream.

---

## 1. Regras obrigatórias (valem para todo agente)

1. Leia e siga `AGENTS.md`, `AI_POLICY.md`, `CONTRIBUTING.md` e os guias em `contrib/guidelines/`
   relevantes à tarefa. Eles têm prioridade sobre este documento.
2. **O humano (dono do repositório) decide.** Não comente, abra ou revise issues/PRs no GitHub.
   Não escreva mensagens de commit, títulos ou descrições de PR prontas para colar.
3. **Commit e push somente quando o humano pedir**, usando a mensagem que ele fornecer. Não faça
   rebase, merge ou reescrita de histórico sem motivo concreto aprovado por ele.
4. Branch de trabalho: `claude/quirky-ptolemy-fuz2pi` (base: `eb5cc45b`). Não crie nem use outros
   branches sem autorização.
5. **Os arquivos `.art` de amostra do usuário são trabalho de cliente: nunca os coloque no
   repositório, em artefatos públicos ou em serviços externos.** Testes usam apenas o fixture
   sintético (`importtests/artcam_fixture.py`).
6. **Não tente decifrar `VectorDocument`** (stream cifrado). Contornar proteção de software
   proprietário está fora do escopo, por motivos legais e de aceitação no upstream.
7. Preserve finais de linha. `src/Mod/Import/Init.py` usa **CRLF**; os demais arquivos tocados
   usam LF. Edite em modo binário ou com ferramenta que preserve o original.
8. Python: `black --line-length 100` (versão do `.pre-commit-config.yaml`), `pyflakes` sem avisos.
9. Nunca afirme que algo foi testado se não foi. Relate verificações bloqueadas.
10. Antes de responder ao usuário: se não há FreeCAD executável, diga isso explicitamente.

---

## 2. Protocolo de coordenação entre agentes (sem conflitos)

Toda comunicação entre agentes passa por [LOG.md](LOG.md). Ele é a fonte da verdade.

1. **Ao iniciar a sessão:** leia o LOG inteiro, rode `git status` e `git log --oneline -5`,
   e compare com a última entrada do LOG. Se houver divergência (arquivos alterados que nenhuma
   entrada explica), **pare e reporte ao humano** antes de editar.
2. **Reivindique antes de trabalhar:** adicione uma entrada `CLAIM` com o ID da tarefa (seção 7)
   e a lista exata de arquivos que vai alterar. Só uma tarefa ativa por agente.
3. **Exclusão por arquivo:** não edite um arquivo listado num `CLAIM` ativo de outro agente.
   Se precisar dele, adicione uma entrada `REQUEST` endereçada ao dono e aguarde/peça ao humano.
4. **Ao terminar ou pausar:** adicione `DONE` ou `PAUSE` com o relatório (modelo no LOG):
   o que mudou, por quê, evidência (comandos e saídas), testes executados/bloqueados,
   limitações e próximos passos. Um `DONE`/`PAUSE` libera os arquivos reivindicados.
5. **Descobertas sobre o formato** (novos campos, tipos de span, diferenças de versão) vão numa
   entrada `FINDING` **e** na seção 5 deste README, com o offset/arquivo de evidência.
6. **Bloqueios** (permissão negada, ferramenta ausente, decisão do humano necessária) vão numa
   entrada `BLOCKED`. Não contorne bloqueios de permissão.
7. Entradas são **somente adicionadas** (append-only), nunca editadas ou apagadas, exceto para
   marcar um `CLAIM` como encerrado referenciando a entrada `DONE`/`PAUSE`.
8. Use timestamps ISO-8601 UTC e um identificador de agente estável (ex.: `agent-B`).

---

## 3. Contexto do pedido do usuário

- O usuário tem muitos projetos do **ArtCAM** (versões 2008 e 2013). O ArtCAM foi
  **descontinuado** pela Autodesk, e ele quer abrir esses arquivos no FreeCAD.
- Os arquivos são de clichês de magnésio (fresadora Roland MDX): perfis, desbastes de cavidade,
  reconhecimento de altura, gravações.
- Idioma de trabalho com o usuário: **português**.

---

## 4. Estado atual (base para continuar)

**Nada foi commitado.** As alterações estão só na árvore de trabalho (ver LOG, entrada 0001).

| Arquivo | Estado | Papel |
| --- | --- | --- |
| `src/Mod/Import/artcam/__init__.py` | novo | pacote |
| `src/Mod/Import/artcam/cfb.py` | novo | leitor Compound File Binary (OLE2), Python puro, sem dependências |
| `src/Mod/Import/artcam/reader.py` | novo | decodifica percursos, nomes, versão, cabeçalho do relevo; sem FreeCAD |
| `src/Mod/Import/importArtCAM.py` | novo | integração FreeCAD: `open()`, `insert()`, `import_file()` |
| `src/Mod/Import/importtests/TestImportArtCAM.py` | novo | 5 testes |
| `src/Mod/Import/importtests/artcam_fixture.py` | novo | gera `.art` sintético (escritor CFB mínimo) |
| `src/Mod/Import/Init.py` | alterado (CRLF) | `addImportType("ArtCAM project toolpaths (*.art *.ART)", "importArtCAM")` |
| `src/Mod/Import/CMakeLists.txt` | alterado | `artcam_SRCS`, cópia para o build, `INSTALL` em `Mod/Import/artcam` |
| `src/Mod/Import/TestImport.py` | alterado | importa `TestImportArtCAM` |
| `artcam-handoff/` | novo | este material (não vai para o upstream) |

**Comportamento no FreeCAD:** cria um `App::DocumentObjectGroup` com o nome do arquivo; dentro,
um `Part::Feature` por percurso (`Label` = nome do percurso; propriedade `Tool` no grupo
"ArtCAM"); `Shape` = compound de wires com `Part.LineSegment` e `Part.Arc` (3 pontos). Contornos
desconectados viram edges soltas. Mensagem no console explica que os vetores são cifrados e que
as linhas são trajetórias do centro da ferramenta.

**Verificação feita:**
- `cfb.py` comparado com `olefile` nos 2 arquivos do usuário: 121 streams idênticos byte a byte.
- `reader.py` nos 2 arquivos: 19 percursos, ~40 mil spans, 1 contorno ilegível (percurso
  "Referencia" do `Prod_Mag_3mm`, erro de preâmbulo). Geometria renderizada e conferida
  visualmente (logo "BRONX", grades 3×3 e 4×5, hachuras de desbaste).
- Fixture validado com `olefile` e com o reader (perímetro 44 + 4π mm; ponto médio do arco correto).
- `test_read_project` e `test_arc_midpoint` passaram com stubs de `FreeCAD`/`Part`.
- `black` e `pyflakes` limpos.

**Não verificado (bloqueado):**
- `test_import_toolpaths`, `test_insert_into_existing_document`, `test_reject_invalid_file`
  exigem FreeCAD real. Não há FreeCAD no contêiner; o download via micromamba foi **negado pela
  política de permissões**. FreeCAD não foi compilado.
- Arquivos do **ArtCAM 2013**: nenhuma amostra disponível.
- Commit/push: **negado pela política**; aguarda pedido explícito do humano com a mensagem dele.

**Itens a confirmar com o humano:** linha de copyright dos arquivos novos
(`SPDX-FileCopyrightText: 2026 The FreeCAD project contributors` é um placeholder).

---

## 5. Especificação do formato decodificado (ArtCAM Pro 2008.151)

Todos os inteiros são little-endian. `i` = int32, `I` = uint32, `H` = uint16, `d` = double.
Unidades: milímetros.

### 5.1 Contêiner

Compound File Binary ([MS-CFB]), v3 (setores de 512 B). Assinatura `D0 CF 11 E0 A1 B1 1A E1`.
Streams observados:

```
SummaryInformation                         metadados OLE (app "ArtCAM Pro")
ArtCAM/VersionInfo/VersionA                versão
ArtCAM/Models/Model1/VectorDocument        VETORES — CIFRADO (não ler)
ArtCAM/Models/Model1/VectorLayers          nomes das camadas (UTF-16, ex. "Camada 1")
ArtCAM/Models/Model1/Parameters            63 B, tamanho do modelo (não decodificado)
ArtCAM/Models/Model1/Preview               miniatura
ArtCAM/Models/Model1/ImageManager/Image1/* imagem de cor (ImageData 192001 B)
ArtCAM/Models/Model1/{Lights,Material}Shading, ValueList, NotesText, ModelUuid, View0/*
ArtCAM/Reliefs/Relief1                     relevo (cabeçalho texto + dados)
ArtCAM/ReliefLayers/ReliefLayer1/{Relief,ReliefLayer,ReliefLayer2}
ArtCAM/ToolpathData/#ToolpathList          ordem dos percursos (ASCII)
ArtCAM/ToolpathData/#UnicodeToolpathList   idem em UTF-16
ArtCAM/ToolpathData/<id27>/Data2           GEOMETRIA DO PERCURSO
ArtCAM/ToolpathData/<id27>/Parameters      nomes da ferramenta e do percurso
ArtCAM/ToolpathData/<id27>/RampData        6 B
ArtCAM/OA_ToolpathData/OA_TOOLPATH_MANAGER parâmetros serializados (ver 5.8)
ArtCAM/CabinetManager/OA_CABINET_MANAGER
```

### 5.2 `VersionA`

`<6i>` = `9, 1, 1, 2008, 151, 32`, depois string `I count + UTF-16` "ArtCAM 2008.151 Unicode",
seguida de hashes em UTF-16. O reader extrai o texto com regex `ArtCAM[ \w.]*?\d[\d.]*`.

### 5.3 `#ToolpathList`

`H versão(=1)`, `H contagem`, depois `contagem × (H tamanho + ASCII)`. Ids com 27 caracteres.

### 5.4 `Parameters` (por percurso)

Contém duas strings `I contagem + UTF-16`: **nome da ferramenta** e depois **nome do percurso**
(ex. offset 0x1a7 / 0x1eb em um arquivo). O reader pega as duas últimas strings válidas.
O restante (doubles: avanços, passo, profundidades?) não foi decodificado.

### 5.5 `Data2` — geometria do percurso

**Cabeçalho** (layout parcialmente conhecido):

```
i 3, H 0, i 1, i 1, i 1, 12×00                    (0x00..0x1d)
FF FF 01 00, H len, ASCII nome-da-classe          tpmContourGroupDrivePicture  (fechado)
                                                  tpmOpenContourGroupDrivePicture (aberto)
i 1, i 0, i 0, d 0.001, d 0.01
i 2, i 1, i 0, [i 1]?, i N, N × d                 N = níveis de Z (profundidades negativas,
                                                  ex. -0.2 … -2.0); o "i 1" opcional varia
                                                  entre percursos -> NÃO confiável ainda
i 2, i 0, i 1, i nContornos?                      (não confirmado)
```

**Contorno** (localizado pela regex `06 00 00 00 01 00 00 00 (00|01) 00 00 00`):

```
i 6               tipo do objeto
i 1               versão
i closed          1 = fechado, 0 = aberto
d tolerance       0 < tol < 1e-2  (vistos: 1e-5, 1e-8)
d 0.0             reservado (deve ser 0)
I id              identificador do contorno
i flags           -1 ou 1
i nSpans
nSpans × span
```

**Span:**

```
i a               1 para arco, 0 para linha (não usado)
i type            0 = linha, 2 = arco, 13 = span inicial (ponto, comprimento zero)
d x1, d y1, d x2, d y2
type 2:  d bulge, d tol(1e-4)
type 13: 4 bytes extras (i 1)
```

`bulge = tan(θ/4)`, convenção DXF: positivo = anti-horário. Ponto médio do arco:
`M + s·(dy, -dx)/c`, com `s = bulge·c/2`, `c` = corda e `(dx, dy) = fim − início`.
Verificado: canto arredondado de raio 6 de um quadrado 182×182 (bulge −0,4142 em percurso horário).

**Após os contornos:** tabela de inteiros (topologia/ordem?) não decodificada.

**Tipos de span desconhecidos:** 5 e 12 apareceram só numa varredura antiga e mais frouxa,
provavelmente falsos positivos. O reader descarta o contorno com tipo desconhecido e conta em
`skipped_contours`.

**Semântica:** as linhas são a **trajetória do centro da ferramenta** (passadas calculadas),
não os vetores de projeto. Desbastes de área aparecem como hachuras/offsets.

### 5.6 `Relief1`

Cabeçalho de texto (latin-1, linhas CRLF):

```
  Relief  RELIEF FILE   Relief                          23 APR 2025 13.58.04
  Relief is 4000 pixels wide by 4000 pixels high
  In real units the relief is 400.00mm wide by 400.00mm high
  Maximum height in the relief is 0.00mm, minimum height is 0.00mm
  Position of the relief is X:-200.000mm Y:-200.000mm Z:0.000mm
  Vertical resolution for points in the relief is 0.0000mm
  Maximum height range which can be represented in the relief is +/- 1.000mm
```

Depois vem uma linha numérica ("400.000000 400.0000000.000000 … 32767.000000 (-200…"), seguida
de dados binários de baixa entropia (provavelmente comprimidos ou RLE) que terminam em
`87 65 43 21`. **Formato dos dados de altura desconhecido:** as duas amostras têm relevo plano.
O valor 32767 sugere alturas em int16 escaladas por "height range".

### 5.7 `Preview`

`B 1`, `I largura(120)`, `I altura(120)`, depois `largura×altura×4` bytes (57609 = 1+8+57600).
Provavelmente BGRA/BGRX. Não confirmado.

### 5.8 `OA_TOOLPATH_MANAGER`

Serialização de classes (`OA_ToolpathList`, `OA_ToolpathGroup`, `OA_ProfileToolpath`,
`OA_2DAreaClearanceToolpath`, `OA_Tool`, `tpmDB_SlotDrillTool`, `wuNamedValueList`,
`wuNamedListNodeDouble/Integer/Bool/String`) com pares nome→valor: `MaximumDepth`,
`ProfileOutside`, `ClimbMill`, `DoRamping`, `LastPassThickness`, `LeadInOutDistanceMM`,
`ToolFinishZ`, etc. Registro de classe: `FF FF 01 00 H len nome`. É o melhor candidato para
**profundidades e parâmetros de corte**. Não decodificado.

### 5.9 `VectorDocument`

Entropia 7,9997 bits/byte, tamanho múltiplo de 16, sem cabeçalho, não é zlib/lzma/bz2 →
**cifra de bloco**. Fora de escopo (regra 6).

---

## 6. Ambiente e comandos

- Contêiner na nuvem, efêmero. **Arquivos fora do repositório se perdem** (scratchpad, uploads).
- As amostras do usuário estavam em `/root/.claude/uploads/<sessão>/*.art`, que só existe na
  sessão original. Peça ao humano para reenviar se precisar. Nunca copie para o repositório.
- Sem FreeCAD. Python 3.13 disponível. `olefile`, `black` e `pyflakes` foram instalados via pip
  na sessão original e podem não existir na sua.
- Playwright/Chromium pré-instalados (servem para renderizar SVG → PNG).

Testes isolados, sem FreeCAD, usando stubs:

```bash
cd src/Mod/Import
mkdir -p /tmp/stubs
printf 'class _Qt:\n    @staticmethod\n    def translate(c, t): return t\nQt=_Qt()\nclass _D:\n    def __init__(s,n): s.Name=n\ndef getDocument(n): raise NameError(n)\ndef newDocument(n): return _D(n)\ndef closeDocument(n): pass\n' > /tmp/stubs/FreeCAD.py
echo 'class OCCError(Exception): pass' > /tmp/stubs/Part.py
PYTHONPATH=/tmp/stubs:. python3 -m unittest -v \
  importtests.TestImportArtCAM.TestImportArtCAM.test_read_project \
  importtests.TestImportArtCAM.TestImportArtCAM.test_arc_midpoint
```

Suíte completa (exige FreeCAD compilado ou instalado):

```bash
FreeCADCmd -t TestImport
```

Inspecionar um `.art` e gerar uma prévia SVG (ferramenta desta pasta):

```bash
python3 artcam-handoff/tools/artcam_inspect.py caminho/arquivo.art --svg saida.svg
```

Teste manual em um FreeCAD 1.x instalado: copiar `artcam/` e `importArtCAM.py` para
`<FreeCAD>/Mod/Import/` e, no console Python, rodar
`import importArtCAM; importArtCAM.open(r"caminho\arquivo.art")`.

Formatação:

```bash
black --line-length 100 src/Mod/Import/artcam src/Mod/Import/importArtCAM.py src/Mod/Import/importtests/TestImportArtCAM.py src/Mod/Import/importtests/artcam_fixture.py
```

---

## 7. Backlog de tarefas (reivindique no LOG pelo ID)

| ID | Tarefa | Arquivos prováveis | Depende de | Prioridade |
| --- | --- | --- | --- | --- |
| T1 | Rodar a suíte completa num FreeCAD real; corrigir falhas | `importArtCAM.py`, testes | FreeCAD disponível | alta |
| T2 | Validar com amostras do **ArtCAM 2013**; ajustar o reader se o layout mudar | `artcam/reader.py`, fixture, README §5 | amostras do humano | alta |
| T3 | Decodificar profundidades/Z: níveis do cabeçalho do `Data2` e/ou `OA_TOOLPATH_MANAGER`; expor como propriedade (ex. `Depths`, `App::PropertyFloatList`) | `reader.py`, `importArtCAM.py`, testes | — | média |
| T4 | Decodificar dados de altura do relevo; importar como malha (avaliar a dependência de Mesh em `Mod/Import`) | `reader.py`, novo módulo | amostra com relevo real | média |
| T5 | Conversor em lote `.art` → DXF sem FreeCAD (oferecido ao usuário, aguarda resposta) | `artcam-handoff/tools/` ou novo script | decisão do humano | média |
| T6 | Investigar o contorno ilegível ("Referencia", erro de preâmbulo) | `reader.py` | amostra `Prod_Mag_3mm` | baixa |
| T7 | Opção de recuperar o vetor de projeto aproximado via offset pelo raio da ferramenta (raio extraído do nome/`OA_Tool`) | `importArtCAM.py` | T3 (parâmetros da ferramenta) | baixa |
| T8 | Importar a miniatura `Preview` (ex. como imagem no documento) | `reader.py`, `importArtCAM.py` | — | baixa |
| T9 | Preparação para o upstream: revisão final, remover `artcam-handoff/`, confirmar copyright, divulgação de IA (AI_POLICY) | vários | humano | — (só com o humano) |

Regras do backlog: tarefas com dependência de amostra ou de decisão só começam depois que o
humano fornecer o que falta. Ao concluir, atualize esta tabela numa entrada `DONE`, sem apagar
linhas.
