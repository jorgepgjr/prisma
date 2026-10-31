# Publicações — biblioteca escolar

## Direção

Produto: gestão dos momentos compartilhados com as famílias no portal Prisma.
Caráter: organizado como um arquivo escolar, cuidadoso com as fotografias e direto nas ações.
Mundo: biblioteca de registros de atividades, turmas e seus destinatários.
Momentos: localizar uma legenda; conferir as fotos e os alunos antes de alterar a publicação.
Assinatura: miniaturas consistentes e uma legenda em destaque; detalhes completos à direita.

## Diagnóstico anterior

- `page.tsx`, listagem: botões Ver/Editar/Excluir empilhados e avisos repetidos de leitura criavam ruído.
- `page.tsx`, filtros: card e título extra competiam com o título principal; faltavam data e ordenação.
- `page.tsx`, visualização: mosaico recortava as fotos e obrigava a percorrer todas de uma vez.
- `page.tsx`, linhas: dimensões e blocos de metadados ampliavam excessivamente cada registro.

## Decisões

1. Espaçamento: base de 4 px; linhas de 136 px; miniaturas de 88 px no desktop e 80 px no mobile.
2. Cor: fundo atual do Prisma, superfícies brancas, cinzas para metadados, azul para ação e seleção; vermelho só na exclusão/erro.
3. Ícones: Lucide, preservando os já usados no portal; sem imagens decorativas novas.
4. Texto: legenda real, sem título inventado; mensagens específicas e contagem abaixo dos filtros.
5. Tipografia: Geist existente; pesos 400/500/600; legenda de 14 px na linha, 15 px nos detalhes.
6. Layout: toolbar sem card, lista horizontal, menu contextual, drawer direito de 560 px ou tela cheia no mobile.
7. Detalhes: menu por teclado, foco devolvido ao disparador, estado ativo, filtros mantidos, respostas abortadas após fechar.
8. Imagens: dados reais; capa na lista; detalhes/ampliação com `object-contain`, sem cortes e com recuperação de erro.
9. Movimento: entrada do drawer em 160 ms, desabilitada com preferência por movimento reduzido; sem efeitos decorativos.

## Integrações e limites

- APIs existentes de publicações, fotos e alunos; nenhuma alteração de banco ou API nesta reformulação.
- `can_manage` retornado pelo servidor controla as ações e é revalidado antes de editar/excluir. A autorização definitiva permanece no backend.
- Modal e fluxo de criação/edição preservados em `PublicationEditor.tsx`; navegação e autenticação reutilizadas.
- Filtros locais combinam legenda, turma, professor, alunos, datas e ordem. A turma continua sendo filtrada também no servidor.
- Renderização progressiva de 25 registros; a API atual ainda entrega a lista autorizada inteira. Paginação de rede não foi adicionada.
- Nenhum registro de demonstração foi criado para preencher a interface. As fixtures existem apenas nos testes.
- Não foi possível conferir pixels, rolagem real e comportamento nativo de foco em navegadores: o acesso automatizado ao navegador está bloqueado neste ambiente. Os testes DOM não substituem essa revisão.

## Crédito metodológico

Revisão orientada por **unslop**, de Damir Sokolovsky ([@heydamir](https://x.com/heydamir)), CC BY 4.0. A identidade visual do Prisma foi preservada.

## Arquivos desta reformulação

- `frontend/app/publications/page.tsx`: entrada da rota e Suspense.
- `frontend/app/publications/PublicationsWorkspace.tsx`: layout, toolbar, listagem e integração com os endpoints existentes.
- `frontend/app/publications/PublicationActions.tsx`: menu contextual acessível.
- `frontend/app/publications/PublicationDrawer.tsx`: detalhes, carrossel e ampliação.
- `frontend/app/publications/PublicationImage.tsx`: foto com tratamento de falha.
- `frontend/app/publications/PublicationEditor.tsx`: formulário existente extraído, sem alterar o contrato de salvamento.
- `frontend/app/publications/model.ts`: tipos, filtros combinados e ordenação.
- `frontend/app/publications/publications.module.css`: drawer responsivo e movimento reduzido.
- `frontend/app/publications/DESIGN.md`: direção visual e limites.
- `frontend/tests/publications.test.tsx` e `frontend/tests/setup.ts`: testes DOM/lógica e configuração de dialogs no ambiente de testes.
- `frontend/vitest.config.mts`: configuração do executor de testes.
- `frontend/package.json` e `frontend/package-lock.json`: ferramentas de teste, somente como dependências de desenvolvimento.
- `GUIA_DE_TESTES_E_FLUXOS.md`: checklist atualizado e resultados.
