# FC27 Kit Generator

Guia de uso: [passo a passo com a foto do Cruzeiro](PASSO_A_PASSO.md).

## Gerar a partir de foto — projeção regional assistida

O botão **Gerar camadas e conferir em 3D** pode ser usado diretamente, sem recalcular a prévia antes. Ele valida os quatro pares, informa quantos pontos faltam em cada painel e fica bloqueado somente durante o cálculo. **Recalcular prévia** continua disponível para revisar o resultado antes de aplicar.

Use **Gerar a partir de foto** no cabeçalho, após selecionar Collar 0 manga curta ou longa. O diálogo tem fotografia, UV extraído da geometria e prévia da composição. Importe a foto original, escolha uma parte anatômica e marque **quatro pares numerados** na mesma ordem ao redor de uma pequena região aproximadamente plana. Arraste os pontos para corrigir. No UV, clique dentro das ilhas brancas: cada ponto é associado a um triângulo real e a pesos baricêntricos. Pontos fora da geometria, quadriláteros degenerados ou cruzados são rejeitados.

Escolha **2 · Contorno da faixa na foto** e clique em pelo menos três pontos ao redor da faixa, dentro da área calibrada. Os quatro pontos de correspondência ficam preservados ao alternar os modos. **Recalcular prévia** detecta uma paleta na região, sugere a cor predominante e projeta o contorno da faixa por uma homografia local. O resultado tem uma camada de base regional e uma camada de polígono com a cor predominante da faixa. **Gerar camadas e conferir em 3D** recalcula usando os pontos atuais, adiciona essas camadas ao projeto e abre a prévia 3D existente. Ctrl+Z desfaz toda a geração; Ctrl+Y restaura. Nada substitui as camadas anteriores.

Repita em outras partes para reconstruir mangas, ombros e faixas distintas. As camadas permanecem editáveis: cor, posição, contorno, rotação e opacidade seguem os controles existentes. Use o editor para adicionar PNG/SVG original por cima de áreas de logos; a projeção não reconstrói marcas. A imagem inteira não é inserida como um retângulo: somente contornos selecionados e cores uniformes são reconstruídos. Isso evita transferir automaticamente sombras e dobras como textura; a estimativa de cor ainda depende da iluminação da foto e deve ser revisada.

O módulo `core/projection/photo_to_uv.py` usa `assets/models/Collar_0.json` ou `Collar_0_LS.json`, com coordenadas UV por canto reais. As correspondências guardam índice de triângulo, pesos baricêntricos, hash SHA-256 da geometria, pontos normalizados na foto e contorno da faixa. A posição 3D da âncora pode ser recuperada pela interpolação dos vértices do mesmo triângulo. **Última calibração** reabre a última correspondência salva somente quando o hash do modelo coincide. O JSON de projeto mantém essas informações e caminhos relativos. Preserve também `output/generated/`, que contém máscaras geométricas independentes, com nomes únicos, usadas pelas camadas geradas.

`core/generation/kit_generator.py` lê a fotografia original para amostrar cores; somente a interface usa miniaturas. A forma vetorial é rasterizada pelo compositor na resolução final de exportação, com recorte regional, máscara da geometria e máscara UV existente. Essa última continua sujeita às divergências de borda documentadas abaixo. O cálculo da geração e da prévia roda em QThread; o diálogo aguarda o cálculo terminar antes de permitir fechamento.

Limites desta versão: homografia **local** por quadrilátero manual, sem recuperação de câmera ou deformação de tecido em superfícies curvas. Divida áreas curvas em pequenas regiões e confira em 3D. Não há inferência de costas/mangas invisíveis: o diálogo avisa que só a região calibrada está coberta; as demais camadas do projeto ficam como estavam. O contorno contrastante é escolhido pelo usuário e sua paleta é calculada automaticamente, sem segmentação semântica automática de todas as faixas. Não há detecção automática de logos, correção fotométrica de sombras ou restauração de padrões complexos. As linhas numeradas nos dois painéis indicam a ordem dos pares.

`cruzeiro_reference.png` agora contém a fotografia frontal enviada pelo usuário. O diálogo abre essa referência automaticamente; a demonstração também a inclui. A calibração das faixas e a fidelidade visual do Cruzeiro ainda precisam ser verificadas no modelo 3D. Testes sintéticos verificam um contorno azul conhecido com erro geométrico máximo inferior a **0,001 pixel em 2048 px**, cor da faixa, máscara, persistência e exportação sem guias; isso mede a transformação controlada, não a fidelidade de uma fotografia real. `tools.check_preview3d` também exercita o diálogo, geração, desfazer/refazer e atualização da textura na camisa real via WebEngine. Capturas: `output/photo_projection_dialog.png` e `output/photo_projection_3d.png`.

## Prévia 3D integrada

A aba **Prévia 3D**, ao lado de Editor UV, carrega os modelos reais já exportados em `assets/models/Collar_0.glb`, `Collar_0_LS.glb` e `Shorts_0.glb`. Não precisa de Blender instalado para visualizar. Three.js r170 e seus módulos estão incluídos localmente com licença MIT; Qt WebEngine serve os arquivos por um servidor restrito a `127.0.0.1`, sem CDN ou internet.

Escolha manga curta no seletor do molde, abra a aba 3D e altere a cor no painel de propriedades. Para adicionar faixas, use o editor UV e retorne à prévia. Arraste com o botão esquerdo para girar, use scroll para zoom e botão direito para pan. Os botões Frente, Costas, Esquerda, Direita e Centralizar reposicionam a câmera. A troca de mangas usa o seletor existente e mantém sua confirmação quando houver calibração. Marque Short para mostrá-lo e use Textura independente do short para carregar seu PNG. Essa textura do short é somente da sessão de prévia e não é salva no JSON nem exportada com a camisa.

A composição limpa é transmitida como PNG RGBA em até 1024 px, com debounce de 180 ms, detecção de conteúdo inalterado, cor sRGB e `flipY=false` para o UV glTF. A geometria é carregada uma vez por modelo e mantida em cache; atualizações de textura preservam a câmera. Renderização ocorre quando há mudanças ou interação. O material original exportado é substituído apenas em memória por um material branco neutro, sem multiplicação pelas cores de vértices. Há iluminação neutra e modo **Cor sem luz** para inspecionar as cores sem sombreamento. Transparência é mantida; superfícies transparentes sobrepostas ainda estão sujeitas à ordenação de transparência do WebGL.

**Teste UV** aplica aos três modelos uma textura numerada, com quatro cores e setas U/TOP. Desmarcar restaura as texturas de trabalho. Não altera camadas, PNG exportado, modelos ou arquivos originais. UVs personalizados suspendem a prévia porque sua correspondência não está validada.

Validação executada: os UVs por canto dos três GLBs correspondem aos dados extraídos do Blender (comparação quantizada a 0,0001, considerando a convenção vertical glTF). As máscaras raster existentes apresentam IoU de **99,4114% na manga curta e 99,6684% na longa** com a cobertura geométrica. Há respectivamente 8.625 e 6.725 pixels geométricos fora das máscaras em 2048²: podem ocorrer pequenos recortes nas bordas. Essa divergência foi reportada e nenhuma máscara ou geometria foi corrigida automaticamente. O short não possui template raster correspondente neste projeto.

Testes adicionais: `python -m tools.validate_preview_uv` gera `output/uv_validation.json`; `python -m tools.check_preview3d` executa integração real Qt WebEngine, valida atualização sem recarregar geometria, preservação da câmera, troca de mangas e short, e grava capturas frontais/traseiras/laterais. Esse teste precisa de sessão gráfica com WebGL; em ambientes restritos pode exigir execução fora do sandbox. As capturas foram inspecionadas com textura numerada. Não houve validação dentro do FC 27. Não foram adicionadas IA ou projeção fotográfica nesta etapa.

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

**`assets/references/cruzeiro_reference.png` contém a foto frontal do Cruzeiro fornecida pelo usuário.** A demonstração a inclui como Frente e o diálogo de projeção a abre automaticamente. Não há escudo do Cruzeiro, Adidas ou Betnacional separado nos arquivos recebidos. Reserve suas posições com landmarks nomeados; quando os originais forem fornecidos, importe-os como arte e use Alinhar a landmark. Nenhum texto aproximado substitui essas marcas na exportação. A gola polo depende também da geometria do modelo: uma textura não muda o formato 3D da gola Collar 0.

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

O editor trabalha com prévia de até 1024 px. Fotos são abertas sob demanda e há cache limitado. Imagens importadas são limitadas a 32 megapixels. Camadas individuais têm limites de memória antes da rotação; reduza dimensões ou resolução se receber esse aviso. A composição 2D usa CPU; a prévia 3D usa WebGL e memória gráfica, com texturas reduzidas e três modelos em cache.

**Compatibilidade exata com FC 27 não validada.** É necessário comparar uma exportação com uma textura funcional e testá-la no pipeline de modding/modelo do usuário. Este protótipo não exporta DDS, normal maps, mapas de material ou pacotes de mod. A visualização 3D usa os GLBs extraídos do arquivo fornecido.

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

A correspondência foto → UV por regiões planas está disponível no novo diálogo descrito acima. Remoção automática de dobras/sombras, fechamento automático de costuras e reconhecimento de logos continuam pendentes.

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
