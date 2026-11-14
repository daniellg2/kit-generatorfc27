# Gerar uma textura a partir da foto do Cruzeiro

## Abrir a versão atual

1. Se já estiver usando o aplicativo, salve o projeto e feche a janela antes de atualizar.
2. Na pasta do repositório, execute `git pull`. Se houver alterações locais, preserve-as antes de atualizar.
3. Dê dois cliques em `start_windows.bat`. Em uma instalação nova, é necessário Python 3.11 ou superior; o script instala as dependências na primeira execução.
4. Escolha **Collar 0 · manga curta** no painel esquerdo.
5. Clique em **Gerar a partir de foto**. A foto frontal do Cruzeiro incluída no projeto será carregada automaticamente.

## Fazer a primeira projeção

Comece com uma pequena área branca do torso ou uma região de manga que contenha uma faixa. Esta versão trabalha por partes aproximadamente planas. Cada geração adiciona uma base regional e, se selecionado, um contorno colorido; ela não reconstrói a camisa inteira com um clique.

1. Escolha a região anatômica no seletor: Frente, Manga esquerda, Manga direita ou Ombro, por exemplo.
2. No modo **1 · Quatro correspondências**, marque quatro cantos ao redor da área na foto. Marque os quatro pontos equivalentes no painel UV geométrico, dentro das ilhas brancas.
3. Os números representam pares: foto 1 corresponde a UV 1, e assim por diante. Percorra o contorno sem cruzar as ligações. A orientação de cada ilha UV deve ser conferida na prévia 3D; a imagem UV não tem a mesma aparência de uma camisa vestida.
4. Se os pares estiverem trocados como no erro de quadrilátero cruzado, use **Ordenar cantos** no modo 1. O botão ordena os cantos independentemente nos dois painéis, começando pelo superior esquerdo e seguindo o contorno. Confira a correspondência: em uma ilha rotacionada essa ordenação pode não representar a superfície desejada. Arraste os pontos para ajustar.
5. Para projetar uma faixa, selecione **2 · Contorno da faixa na foto**. Clique em pelo menos três pontos ao redor da área azul ou amarela, dentro do quadrilátero calibrado. Os pontos de correspondência permanecem guardados.
6. Clique em **Recalcular prévia** para conferir o resultado. A cor é sugerida com base na foto; revise-a para evitar cores afetadas por sombra.
7. Clique em **Gerar camadas e conferir em 3D**. Esse botão também funciona diretamente, sem recalcular a prévia antes. Se faltarem pontos ou houver cruzamentos, ele informa o problema.

## Conferir e corrigir

1. A geração abre a aba **Prévia 3D** e adiciona camadas ao projeto existente.
2. Arraste com o botão esquerdo para girar, use scroll para zoom e botão direito para pan. Os botões Frente, Costas e laterais ajudam a verificar a posição.
3. Volte ao **Editor UV** e selecione a camada gerada no painel esquerdo. Ajuste cor, posição, tamanho, rotação, opacidade e região de recorte nas propriedades.
4. Use **Ctrl+Z** para desfazer a geração inteira e **Ctrl+Y** para refazer. Se for repetir a mesma região para corrigir o resultado, desfaça ou remova as camadas anteriores para evitar sobreposição.
5. Repita o processo separadamente para cada faixa azul, faixa amarela e detalhe de ombro. Use **Última calibração** para recuperar a correspondência mais recente do mesmo modelo.

## Salvar e exportar

1. Salve o projeto com **Ctrl+S**. O JSON contém os caminhos das fotos e máscaras, as camadas e as correspondências.
2. Preserve os arquivos de referência, os modelos e as máscaras em `output/generated/` junto com o projeto. Eles não são incorporados no JSON nem enviados automaticamente ao GitHub.
3. Clique em **Exportar PNG**, confira a prévia sem guias e escolha o destino. A resolução de exportação é independente da prévia 3D, limitada a 1024 px para desempenho.

## Limites atuais

- Esta é uma reconstrução regional assistida, com contornos manuais e cores uniformes. Não há reconstrução automática completa da fotografia.
- A foto fornecida mostra a frente; costas e detalhes ocultos não são inferidos.
- A gola polo fotografada não corresponde necessariamente à geometria da gola Collar 0. A textura não altera a forma 3D.
- Escudos, Adidas e Betnacional não são redesenhados ou extraídos automaticamente. Importe seus arquivos PNG/SVG originais como camadas quando disponíveis.
- Superfícies curvas exigem regiões menores e revisão em 3D. As máscaras raster têm pequenas divergências de borda já documentadas no README.
- A compatibilidade dentro do FC 27 permanece sem validação no jogo.
