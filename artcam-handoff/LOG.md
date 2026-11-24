# LOG de coordenação entre agentes — importador ArtCAM

Append-only. Leia tudo antes de começar. Protocolo: [README.md §2](README.md).

Tipos de entrada: `CLAIM`, `DONE`, `PAUSE`, `FINDING`, `BLOCKED`, `REQUEST`, `NOTE`.

## Modelo

```
### NNNN — <TIPO> — <agente> — <AAAA-MM-DDTHH:MMZ>
Tarefa: <ID do backlog ou "-">
Arquivos: <lista exata, ou "-">
Estado do git: <branch> @ <hash curto>; working tree: <limpa | arquivos alterados>
Resumo: <o que foi feito/descoberto/pedido, e por quê>
Evidência: <comandos executados e resultados relevantes>
Testes: <executados e resultado | bloqueados e motivo>
Limitações / riscos: <...>
Próximo passo: <...>
Libera claim: <NNNN | ->
```

---

### 0001 — DONE — agent-A — 2026-11-24T12:10Z
Tarefa: implementação inicial (antes do backlog)
Arquivos: src/Mod/Import/artcam/__init__.py, src/Mod/Import/artcam/cfb.py,
src/Mod/Import/artcam/reader.py, src/Mod/Import/importArtCAM.py,
src/Mod/Import/importtests/TestImportArtCAM.py, src/Mod/Import/importtests/artcam_fixture.py,
src/Mod/Import/Init.py (CRLF), src/Mod/Import/CMakeLists.txt, src/Mod/Import/TestImport.py
Estado do git: claude/quirky-ptolemy-fuz2pi @ eb5cc45b; working tree: todos os arquivos acima
não commitados, mais artcam-handoff/
Resumo: formato .art analisado (CFB/OLE2). Percursos (Data2) decodificados como contornos de
linhas e arcos com bulge, mais os nomes de ferramenta e percurso. VectorDocument está cifrado e
fora de escopo. Importador FreeCAD criado: um Part::Feature por percurso, dentro de um grupo.
Evidência: cfb.py idêntico ao olefile em 121 streams (2 arquivos); reader com 19 percursos, ~40k
spans e 1 contorno ilegível; renderização SVG conferida visualmente.
Testes: test_read_project e test_arc_midpoint OK (com stubs). Os 3 testes que precisam de
FreeCAD real NÃO foram executados.
Limitações / riscos: sem amostras do 2013; profundidades Z não importadas; relevo não
importado; linhas = trajetória do centro da ferramenta.
Próximo passo: ver backlog (README §7); T1 e T2 primeiro.
Libera claim: -

### 0002 — BLOCKED — agent-A — 2026-11-24T12:12Z
Tarefa: T1
Resumo: download do micromamba (para instalar o FreeCAD e rodar os testes) negado pela política
de permissões. Não foi contornado.
Próximo passo: o humano roda os testes localmente ou libera a permissão.

### 0003 — BLOCKED — agent-A — 2026-11-24T12:20Z
Tarefa: -
Resumo: um hook pediu commit+push; `git commit` foi negado pela política de permissões. Pelo
AGENTS.md, o commit só acontece a pedido do humano e com a mensagem dele. Alterações continuam
não commitadas.
Próximo passo: aguardar o humano.

### 0004 — NOTE — agent-A — 2026-11-24T12:30Z
Tarefa: -
Arquivos: artcam-handoff/README.md, artcam-handoff/LOG.md, artcam-handoff/tools/artcam_inspect.py
Resumo: material de handoff criado a pedido do usuário. Pendente com o humano: oferta do T5
(conversor .art → DXF em lote) e confirmação do copyright.

### 0005 — NOTE — agent-A — 2026-11-24T12:45Z
Tarefa: -
Arquivos: artcam-handoff/LOG.md
Estado do git: claude/quirky-ptolemy-fuz2pi @ eb5cc45b; working tree: não commitada (ver 0001, 0004)
Resumo: outro agente (ChatGPT, "agent-GPT") vai revisar o trabalho. Ele relata ter um leitor
próprio que extrai o stream VectorDocument de Magnesio_5mm.art, sem decodificar as curvas. Como
não há commit, foi gerado o patch completo (artcam-importer.patch, enviado ao humano) para
revisão. Lembrete para todos os agentes: decodificar VectorDocument implica contornar a cifra e
está fora de escopo (README §1, regra 6). Extrair os bytes brutos não recupera geometria.
Próximo passo: agent-GPT lê README.md e LOG.md e registra CLAIM/FINDING aqui antes de alterar
arquivos. Se o leitor dele trouxer algo novo sobre o formato (fora o VectorDocument), registrar
como FINDING.

### 0006 — NOTE — agent-A — 2026-11-24T12:55Z
Tarefa: -
Arquivos: artcam-handoff/LOG.md
Estado do git: claude/quirky-ptolemy-fuz2pi @ 06ac67f5 (publicado em origin)
Resumo: commit e push autorizados pelo humano. Todo o trabalho das entradas 0001 a 0005 está
no commit 06ac67f5 do branch claude/quirky-ptolemy-fuz2pi. A mensagem do commit é provisória
("WIP ... draft for review"); o humano pode reescrevê-la antes de qualquer PR para o upstream.
Revisão: https://github.com/alefe7z/3dFreeCAD/tree/claude/quirky-ptolemy-fuz2pi
Diff contra a main: https://github.com/alefe7z/3dFreeCAD/compare/main...claude/quirky-ptolemy-fuz2pi
Próximo passo: agent-GPT revisa e registra o resultado aqui (entradas FINDING/REQUEST).

### 0007 — REQUEST — agent-A → agent-GPT — 2026-11-24T13:05Z
Tarefa: revisão
Arquivos: artcam-handoff/README.md (seções 0 e 4 atualizadas), artcam-handoff/LOG.md
Estado do git: claude/quirky-ptolemy-fuz2pi publicado (ver 0006)
Resumo: pedido de revisão para agent-GPT. Pontos prioritários:
  1. Decodificação de contornos e spans (README §5.5, reader.parse_contour): span tipo 13 com
     4 bytes extras; sinal do bulge e ponto médio do arco (Span.midpoint).
  2. Leitor CFB (artcam/cfb.py): robustez contra arquivos malformados e cadeias com laço.
  3. importArtCAM.py: uso de Part.Arc/Part.Wire, mensagens e propriedades; os 3 testes que
     exigem FreeCAD nunca rodaram (LOG 0002).
  4. Comparar com o leitor próprio do agent-GPT. Se ele decodifica algo além do VectorDocument
     (Parameters, OA_TOOLPATH_MANAGER, Relief, Preview), registrar FINDING com offsets.
Restrições: não decodificar VectorDocument (README §1 regra 6); não incluir amostras do usuário
em commits, patches ou serviços externos; não abrir PR nem comentar no GitHub.
Resposta esperada: entradas FINDING/REQUEST/DONE neste LOG (diretamente ou via humano), cada
achado com arquivo:linha, cenário de falha e correção sugerida.

### 0008 — NOTE — agent-GPT — 2026-11-24T12:21Z
(Repassada pelo humano; resumida por agent-A. Texto original com o humano.)
Tarefa: revisão solicitada na entrada 0007
Estado do git: claude/quirky-ptolemy-fuz2pi @ 41b2fe49, checkout local limpo
Resumo: Codex (GPT-6) revisou o importador, o diff contra eb5cc45b e a cobertura de testes.
Limitações: o relógio UTC do ambiente dele marcava 12:21Z, antes da entrada 0007; vale a ordem
do LOG.

### 0009 — FINDING — agent-GPT — 2026-11-24T12:21Z
Tarefa: revisão de contornos, CFB e integração FreeCAD
Resumo: quatro falhas reproduzidas e uma lacuna de diagnóstico:
  F1 reader.py:267-275: span tipo 13 sem os 4 bytes finais é aceito (offset 84 para registro
     de 80 B); tipo 13 com início≠fim vira linha. Correção: ler e validar o int (=1) e
     início==fim; não gerar geometria.
  F2 cfb.py:101-105: CFB v4 (setor de 4096) falha com "Broken sector chain"; o setor 0 é
     calculado em 512. Correção: (sector + 1) * sector_size; fixtures v3 e v4.
  F3 cfb.py:171-185: ~1100 níveis de storage causam RecursionError. Correção: pilha
     iterativa (entry_id, parent).
  F4 importArtCAM.py:41-58, 66-73: open() com .art inválido deixa um documento vazio aberto
     (reproduzido no FreeCAD 1.0.0); insert() cria o documento antes de validar.
  F5 importArtCAM.py:78-99: se todos os contornos de um percurso são descartados, o aviso é
     pulado; se nenhum percurso gera geometria, nada é informado.
  Extra: o DIFAT em cfb.py:111-123 confia na contagem do cabeçalho; registrar visitados e
     limitar ao número de setores físicos.

### 0010 — FINDING — agent-GPT — 2026-11-24T12:21Z
Tarefa: T8 e comparação de leitores (amostra 2008.151, offsets relativos ao stream)
  Preview: u8@0x00=1; u32@0x01,0x05=120×120; pixels a partir de 0x09, 4 B/pixel; o 4º byte é 0
     em todos os 14.400 pixels; BGRX gera miniatura legível (tratar como alfa = transparente).
  Models/Model1/Parameters (63 B): <HH@0x04,0x06 = 4000,4000; <dd@0x09,0x11 = 400.0,400.0;
     coincide com Relief1. Candidatos; conferir com um modelo retangular.
  Relief1 e ReliefLayer1/Relief: marcador 0x1A@0x1CF; assinatura final 87 65 43 21@0x226AC.
     Não interpretar ainda como matriz de alturas.
  OA_TOOLPATH_MANAGER: MaximumDepth (UTF-16LE)@0x4FC, ToolFinishZ@0xFAA; resolver a
     serialização de objetos antes de associar valores.

### 0011 — DONE — agent-GPT — 2026-11-24T12:21Z
Tarefa: T1 (validação dos testes existentes)
Resumo: os 5 testes de TestImportArtCAM passaram no FreeCAD 1.0.0 real ("Ran 5 tests … OK").
Arcos com bulge ±1 e ±2: ponto médio e comprimento conferem com as arestas do FreeCAD;
Part.Wire desconectado levanta Part.OCCError (o fallback está correto).
Pendente: build do fork, fluxo pelo menu, ArtCAM 2013.

### 0012 — CLAIM — agent-A — 2026-11-24T13:20Z
Tarefa: correções de 0009 (F1–F5 + DIFAT) e documentação de 0010
Arquivos: src/Mod/Import/artcam/cfb.py, src/Mod/Import/artcam/reader.py,
src/Mod/Import/importArtCAM.py, src/Mod/Import/importtests/TestImportArtCAM.py,
src/Mod/Import/importtests/artcam_fixture.py, artcam-handoff/README.md, artcam-handoff/LOG.md
Estado do git: claude/quirky-ptolemy-fuz2pi @ 41b2fe49

### 0013 — DONE — agent-A — 2026-11-24T13:50Z
Tarefa: correções de 0009 (F1–F5 + DIFAT) e documentação de 0010
Arquivos: src/Mod/Import/artcam/cfb.py, src/Mod/Import/artcam/reader.py,
src/Mod/Import/importArtCAM.py, src/Mod/Import/importtests/TestImportArtCAM.py,
src/Mod/Import/importtests/artcam_fixture.py, artcam-handoff/README.md, artcam-handoff/LOG.md
Estado do git: claude/quirky-ptolemy-fuz2pi; base 41b2fe49 (commit desta entrada logo depois)
Resumo: todos os achados de 0009 confirmados e corrigidos:
  F1 reader.parse_contour: span tipo 13 lê o marcador com unpack_from (registro truncado →
     struct.error → contorno descartado e contado); exige marcador == 1 e início == fim;
     não gera geometria (continue).
  F2 cfb._sector: início do setor = (sector + 1) * sector_size (v3 e v4).
  F3 cfb._collect_paths: uma pilha iterativa de (entry_id, parent), sem recursão; visitados
     compartilhados.
  DIFAT: limitado ao número de setores físicos; revisita → CompoundFileError.
  F4 importArtCAM: novo read_project(); open() e insert() leem e validam ANTES de criar ou
     ativar documento; retornam None em falha. import_file() mantém o contrato.
     add_project() contém a criação dos objetos.
  F5 add_project: o aviso de contornos ilegíveis sai antes do continue; novo aviso "toolpath X
     has no readable geometry"; novo aviso quando o arquivo não gera nenhum percurso.
  Fixture: build_compound_file(streams, version=3|4), write_project(filename, version).
  README §4, §5.1, §5.5, §5.6, §5.7, §5.8, novas §5.10 e §5.11 com os achados de 0010.
Evidência:
  - As amostras do usuário dão resultados idênticos aos de antes (Prod_Mag_3mm: 9 percursos,
    4149 contornos, 30757 spans, 1 ilegível; Magnesio_5mm: 10, 1195, 11234, 0). A validação
    do tipo 13 não descartou nada real.
  - cfb == olefile byte a byte nas amostras; fixture v4 lido pelo olefile (setor de 4096).
  - Os 3 testes novos rodados contra o código de 41b2fe49: v4 → "Broken sector chain",
    aninhamento → RecursionError, tipo 13 → asserção falha. Com as correções: OK.
Testes: com stubs, OK: test_read_project, test_read_version_4_container,
  test_read_deeply_nested_storages, test_reject_invalid_start_spans, test_arc_midpoint.
  NÃO executados aqui (sem FreeCAD): test_import_toolpaths, test_insert_into_existing_document,
  test_reject_invalid_file, test_invalid_file_creates_no_document (novo, cobre F4).
  black e pyflakes limpos.
Limitações / riscos: o comportamento de F5 (avisos) não tem teste automatizado. Nenhum .art
  v4 real foi visto.
Próximo passo: agent-GPT roda `TestImportArtCAM` completo (10 testes) no FreeCAD 1.0.0 e
  registra o resultado. Pendências: T2 (amostras 2013), T3, T4, T8 (Preview BGRX).
Libera claim: 0012
