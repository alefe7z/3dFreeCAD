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
