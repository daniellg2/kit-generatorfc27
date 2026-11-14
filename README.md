# FC27 Kit Generator

Protótipo desktop para Windows, em português, para reconstrução **manual e assistida** de uniformes em um UV fixo. Python 3.11+, PySide6, Pillow, NumPy e OpenCV. Processamento local por CPU, sem API, IA generativa, CUDA ou modelos grandes. A instalação inicial das dependências precisa de internet; o aplicativo instalado funciona offline.

## Iniciar no Windows

Dê dois cliques em **`start_windows.bat`**. Neste computador, o ambiente `.venv` já foi preparado e as dependências instaladas. O script usa esse ambiente; em outro computador, instale Python 3.11+ e o script criará o ambiente e instalará `requirements.txt`.

Alternativa pelo PowerShell, a partir desta pasta:

```powershell
.\.venv\Scripts\python.exe -m app
```

Instalação manual em uma cópia nova:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app
```

Não mova o ambiente virtual entre computadores. Recrie `.venv` ao transferir o projeto. O Python local instalado em `.runtime` neste computador é usado pelo ambiente atual.

## Primeira textura

1. Escolha **Collar 0 · manga curta** ou **Collar 0 LS · manga longa**, no painel esquerdo. Ambos os guias originais têm 2048 × 2048 pixels e estão preservados em `assets/uv_templates/`.
2. Em **Fotos**, os três exemplos enviados já estão disponíveis. Use **+ Referência** para importar fotografias e indicar Frente, Costas, mangas, gola etc. **Ampliar** abre a imagem com zoom; **Usar como camada** insere a imagem original para ajuste manual. Fotos não são automaticamente desdobradas sobre o UV.
3. Em **Regiões**, clique em **Desenhar região**. Clique nos vértices da parte desejada sobre o UV e pressione **Enter** ou o botão direito para concluir. Nomeie a região. **Backspace** retira o último ponto; **Esc** cancela. Selecione a região e arraste seus pontos amarelos para ajustar. **Redesenhar** substitui seu polígono.
4. Marque a vista correspondente em **Referência da região**. Uma região sem vista associada ou sem referência dessa vista aparece no aviso de cobertura. O aviso verifica disponibilidade, não qualidade ou completude da foto.
5. Adicione **landmarks** na região para centros de escudos, patrocinadores, gola e alinhamentos. Landmarks são guias e nunca entram no PNG. Para mudar um landmark, adicione-o novamente com o mesmo nome ou remova-o e recrie-o.
6. Em **Camadas**, selecione a cor base; altere a cor no painel direito. Crie áreas retangulares com **Cor / forma**, faixas repetidas com **Faixas**, polígonos e curvas pela barra superior. Para faixas verticais use rotação 90°; diagonais usam o ângulo desejado. Polígonos podem ser preenchidos ou somente contorno; curvas passam pelos pontos inseridos.
7. Em **Recortar em**, escolha a região da camada. **Enquadrar na região** ajusta sua caixa à região sem alterar o UV. Posição, dimensões e ângulos permanecem editáveis; o recorte impede arte fora do polígono e do limite global.
8. Use **PNG / SVG** para importar artes originais. Arraste para mover ou use Centro X/Y; ajuste largura, altura e rotação no painel direito. Preserve proporções, espelhe e ajuste opacidade. **Recolorir imagem pelo alfa** preserva o contorno e substitui as cores. Para logos coloridos, mantenha essa opção desligada. **Alinhar a landmark** posiciona o centro da camada em um marco escolhido.
9. Use **Padrão** para importar uma imagem repetida. Ajuste escala do ladrilho, deslocamentos, rotação e opacidade e associe a uma região. Continuidade entre partes exige ajustar fase, escala, orientação e conferir as costuras manualmente; não há correspondência automática de costuras.
10. Use as setas ↑/↓ para ordenar camadas. O topo da lista fica por cima. As caixas de seleção controlam visibilidade. Salve o projeto e abra **Exportar PNG**: confira a prévia sem malha e escolha o destino.

Todos os controles de coordenadas e dimensões usam frações do canvas UV completo, de 0 a 1 dentro da imagem. `x` e `y` são o **centro**, largura/altura são frações dos respectivos eixos. Dimensões continuam independentes da resolução. Rotação positiva é horária. A proporção do canvas é mantida na exportação; os objetos podem ser redimensionados com proporção bloqueada.

**Scroll** faz zoom; **botão central** faz pan; **F** enquadra; **Ctrl+Z / Ctrl+Y** desfaz/refaz; **Ctrl+D** duplica; **Ctrl+N/O/S/Shift+S/E** cria, abre, salva, salva como e exporta. As transformações por arraste são confirmadas ao soltar o mouse. Largura, altura e rotação são ajustadas pelos controles numéricos, sem alças de transformação na primeira versão.

## Limites do UV: guia versus máscara

- `short_sleeve.png`: cópia intacta de **Collar 0.png**.
- `long_sleeve.png`: cópia intacta de **Collar 0 LS.png**.
- `*_mask.png`: máscaras preto/branco independentes; **branco permite arte, preto recorta**.
- A malha azul é uma sobreposição do editor, com opacidade ajustável. A composição exportável nunca lê suas linhas como arte.

As máscaras iniciais foram extraídas das células cinzas dos guias com fechamento morfológico para remover as linhas internas. O vão da gola é mantido, incluindo a pequena ilha interna. **Esse contorno raster é experimental e tem incerteza de pixels nas bordas**: confira-o e substitua por uma máscara revisada para trabalho exato. Alterar a máscara não altera o arquivo guia nem sua topologia.

O botão **Máscara** troca o recorte global. A máscara deve ser um PNG preto/branco, nas mesmas dimensões originais do guia. Para outro molde, use **Carregar UV** e escolha o guia e sua máscara. Não se assume que frente, costas e mangas compartilhem orientação; calibre cada parte manualmente. O polígono define onde recortar, sem fazer deformação ou projeção de perspectiva.

**Salvar calibração** grava um JSON com o molde, máscara, polígonos e landmarks. **Carregar calibração** adiciona regiões de uma calibração do mesmo guia, verificado pelos bytes originais. Não aceita reutilizar silenciosamente regiões de outro UV. Ao trocar o molde, a calibração é limpa e as artes de detalhe ficam ocultas; a operação pode ser desfeita. Camadas vinculadas precisam ser desvinculadas antes de excluir uma região.

## Referências enviadas e demonstração Cruzeiro

Os três exemplos adicionais foram copiados integralmente para `assets/references/example_black.png`, `example_blue.png` e `example_red.png`. São texturas UV já compostas, incluindo suas marcas e textos originais. O programa não os redesenha, não extrai seus logos automaticamente e não presume que o layout seja idêntico ao Collar 0. Para um logo separado, importe seu PNG/SVG original.

Abra **Projeto → Demonstração Cruzeiro** ou `assets/cruzeiro_demo.json`. A demonstração inclui base branca e camadas editáveis nomeadas para detalhes azuis, três listras em cada ombro, faixas azuis/amarelas nas mangas e gola branca. Os detalhes começam **ocultos**, pois a correspondência anatômica ainda precisa de calibração. Associe cada detalhe à região correta, use Enquadrar, ajuste seu tamanho e ative a visibilidade. Para as três listras, ajuste cada faixa separadamente na região de ombro correspondente.

**`assets/references/cruzeiro_reference.png` não foi fornecido.** O projeto de demonstração registra essa ausência em suas notas, em vez de usar uma camisa diferente como se fosse a referência solicitada. Não há escudo do Cruzeiro, Adidas ou Betnacional separado nos arquivos recebidos. Reserve suas posições com landmarks nomeados; quando os originais forem fornecidos, importe-os como arte e use Alinhar a landmark. Nenhum texto aproximado substitui essas marcas na exportação. A gola polo depende também da geometria do modelo: uma textura não muda o formato 3D da gola Collar 0.

## Análise experimental, fase 2

Em Fotos, selecione uma imagem e use **Analisar referência**. A análise local reduz a imagem para até 640 px, tenta segmentação GrabCut com retângulo central, calcula uma paleta de seis cores e detecta linhas de contraste com Canny/Hough. O resultado mostra a máscara e as linhas sobre a referência.

Clique numa cor para criar uma camada editável. Para aceitar uma linha como faixa, selecione antes uma região calibrada. A direção observada na foto é apenas um ponto de partida; posição, largura e orientação UV exigem revisão. Fechar o diálogo rejeita as sugestões restantes. Aceitações podem ser desfeitas pelo histórico.

Não há promessa de separar camisa de fundo em qualquer foto. A máscara pode conter fundo, perder partes e confundir dobras com linhas; a paleta pode incluir sombras e reflexos. Em falha de segmentação, o aplicativo informa que analisou a imagem inteira e mantém as ferramentas manuais disponíveis. A máscara da foto nunca substitui a máscara UV.

## Projetos e recuperação

JSON armazena versão, nome, caminhos de referências, guia/máscara, regiões e landmarks normalizados, camadas em ordem de composição, cores, transformações e largura de exportação. Os caminhos são relativos à pasta do JSON quando possível e absolutos entre unidades diferentes do Windows. As imagens não são incorporadas: mantenha os arquivos juntos ao compartilhar o projeto.

O salvamento escreve um temporário e substitui o JSON somente após sucesso. Arquivos originais não são alterados; exportar por cima de um guia, máscara, referência ou arte do projeto é bloqueado. Arquivos ausentes são relocalizados no menu Abrir. JSON inválido ou assets inválidos produzem mensagens e preservam o projeto aberto.

O histórico mantém até 40 estados de metadados, sem duplicar pixels. A cada 45 segundos de alterações não salvas, grava `output/autosave.recovery.json`; a próxima inicialização oferece recuperação. Fechar normalmente após salvar ou descartar remove essa cópia. `output/app.log` registra erros. A recuperação é local e de uma única sessão; use uma instância do editor por pasta de projeto.

## Exportação e memória

PNG RGBA, resolução original ou largura configurável com altura proporcional, até **16 megapixels** (4096 × 4096 para estes UVs). O resultado contém somente as camadas visíveis recortadas. A prévia é reduzida; a exportação recompõe na resolução escolhida. As caixas de seleção, grade, textos, landmarks, regiões e linhas UV são apenas objetos da interface e não entram no compositor.

O editor trabalha com prévia de até 1024 px. Fotos são abertas sob demanda e há cache limitado. Imagens importadas são limitadas a 32 megapixels. Camadas individuais têm limites de memória antes da rotação; reduza dimensões ou resolução se receber esse aviso. Nenhum recurso exige GPU. Um PC com 4 GB de VRAM pode usá-lo sem alocar essa VRAM; a memória RAM necessária varia com a resolução e as imagens importadas.

**Compatibilidade exata com FC 27 não validada.** É necessário comparar uma exportação com uma textura funcional e testá-la no pipeline de modding/modelo do usuário. Este protótipo não exporta DDS, normal maps, mapas de material, pacotes de mod nem visualização 3D.

## Arquitetura

| Pasta | Responsabilidade |
|---|---|
| `app/` | Inicialização, tema, janela com três painéis, canvas Qt, histórico e demonstração |
| `core/uv/` | Leitura de guias, máscara raster e polígonos normalizados |
| `core/layers/` | Dataclasses serializáveis e validação de estado |
| `core/rendering/` | Rasterização SVG via QtSvg, transformações Pillow, repetição, recortes e PNG |
| `core/detection/` | Protocolo `ReferenceAnalyzer`, resultado `Analysis` e implementação OpenCV substituível |
| `core/projects/` | Persistência atômica JSON, caminhos relativos e arquivos ausentes |
| `assets/` | Guias recebidos, máscaras derivadas, referências, espaço para logos e JSON de demonstração |
| `tests/` | Testes de composição, coordenadas, persistência, análise e integração Qt |
| `tools/` | Preparação determinística de assets e captura offscreen para inspeção |
| `output/` | Exportações, prévias de QA, recuperação e log |

O compositor recebe apenas o projeto e o tamanho de saída. A malha e as guias são adicionadas depois pela interface; isso evita vazamento para o PNG. SVG é rasterizado pelo QtSvg já fornecido com PySide6, sem Cairo nativo extra. O protocolo de análise permite acrescentar um modelo local posteriormente, sem acoplá-lo ao compositor; nenhum modelo é incluído agora.

## Estado da entrega

| Etapa | Estado |
|---|---|
| Fase 1 | Editor funcional, UVs, calibração, camadas, PNG/SVG, transformações numéricas, composição, histórico, JSON e exportação |
| Fase 2 | Paleta, segmentação e linhas experimentais; padrões repetidos e alinhamento por landmarks disponíveis |
| Fase 3 | Contrato de análise preparado; sem modelos instalados |

A correspondência foto → UV, a remoção de perspectiva/dobras/sombras, o fechamento automático de costuras e o reconhecimento de logos não foram implementados. A versão entrega o fluxo manual com recorte fixo, sem gerar uniformes aleatórios ou regiões desconhecidas.

## Testes

Sem dependência de pytest:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Em um sandbox que bloqueie a pasta temporária do Windows:

```powershell
New-Item -ItemType Directory -Force .test-tmp | Out-Null
$env:TEMP = "$PWD/.test-tmp"
$env:TMP = "$PWD/.test-tmp"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os 18 testes verificam dimensões, alfa, limites dos dois UVs, ausência da malha, composição e ordem, visibilidade/opacidade, proporção, rotação/espelhamento/recoloração, padrões, polígonos/curvas, coordenadas normalizadas em duas resoluções, JSON relativo e gravação inválida, assets ausentes, proteção dos originais, análise sem mutar o projeto e o fluxo Qt de regiões, landmarks, camadas e desfazer/refazer. Incluem arraste por eventos reais do mouse e comparação pixel a pixel do PNG exportado com a composição limpa, mesmo com grade e malha ativas no editor. Passaram no ambiente local; as telas foram inspecionadas em renderização offscreen nas duas resoluções abaixo.

Para capturar as telas de QA em 1480 × 940 e 1100 × 760:

```powershell
.\.venv\Scripts\python.exe -m tools.visual_check
```

As máscaras já estão incluídas. Para uma cópia que tenha somente os dois guias, `python -m tools.prepare_assets` gera máscaras faltantes e o JSON da demonstração. O script preserva máscaras existentes revisadas.
