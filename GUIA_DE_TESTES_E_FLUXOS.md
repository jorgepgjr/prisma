# Guia de testes e fluxos dos aplicativos

Este documento descreve como iniciar e testar o ecossistema formado por:

- **Prisma:** portal web e API da escola.
- **TinhaPhone:** aplicativo usado pelo professor para fotografar e enviar imagens.
- **TinhaKids:** aplicativo usado pelas famílias para visualizar publicações e portfólios.

## 1. Visão geral do fluxo

```text
Coordenação cadastra profissionais, turmas e crianças no Prisma
                              ↓
Professor configura o TinhaPhone com sua conta e uma turma
                              ↓
Professor tira uma foto e o TinhaPhone envia para o Prisma
                              ↓
Worker do Prisma processa a foto e organiza faces em grupos
                              ↓
Coordenação revisa fotos, fila e grupos faciais no Prisma
                              ↓
Coordenação vincula a criança a uma conta familiar
                              ↓
Professor ou Coordenação cria uma publicação ou portfólio
                              ↓
Responsável entra no TinhaKids e visualiza o conteúdo da criança
                              ↓
Coordenação aprova fotos específicas para o Marketing
                              ↓
Marketing visualiza somente as fotos aprovadas da própria escola
```

## 2. Pré-requisitos

Antes dos testes, confirme que estão instalados:

- Docker Desktop em execução.
- Node.js e npm.
- Python e Pipenv.
- Flutter e um navegador ou emulador Android.

Pastas dos projetos:

```text
jorge/
├── prisma/
├── tinhaphone/
└── tinhakids/
```

## 3. Iniciar o Prisma

### Opção automática no Windows

No PowerShell:

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\prisma
.\iniciar-prisma.ps1
```

Use `-Seed` somente quando quiser apagar e recriar os dados locais:

```powershell
.\iniciar-prisma.ps1 -Seed
```

> **Atenção:** o seed remove definitivamente os dados existentes no banco local.

O inicializador abre o banco, a API, o worker de reconhecimento e o frontend. Deixe as janelas do backend e do worker abertas para acompanhar erros e o processamento da fila.
Na primeira inicialização após esta atualização, a API adiciona as colunas da fila ao banco existente sem recriar nem apagar os registros.

### Opção manual

Banco e API (Terminal 1):

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\prisma
docker compose up -d
cd backend
pipenv install
pipenv run uvicorn app.main:app --reload
```

Worker de reconhecimento (Terminal 2):

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\prisma\backend
pipenv run python worker.py --interval 3
```

Frontend (Terminal 3):

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\prisma\frontend
npm install
npm run dev
```

Endereços:

- Portal: <http://localhost:3000>
- Documentação da API: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`

## 4. Dados criados pelo seed

Um seed limpo cria duas escolas para testar o isolamento dos dados:

- Escola Girassol
- Escola Horizonte

Cada escola recebe:

- Um Coordenador.
- Um Professor.
- Um usuário de Marketing.
- Uma turma chamada Grupo 2.
- Dois alunos: FILHO TESTE e Sofia na Girassol; Pedro e Sofia na Horizonte.
- Dois familiares, cada um vinculado somente ao próprio aluno.
- Duas imagens ilustrativas de teste aprovadas para Marketing, cada uma identificada com um aluno.
- Uma publicação e um portfólio para cada aluno.

Todas as contas de teste, profissionais e familiares, usam a senha:

```text
mypassword
```

### Escola Girassol

| Perfil | E-mail |
|---|---|
| Coordenação | `coordenacao@girassol.com` |
| Professor | `professora@girassol.com` |
| Marketing | `marketing@girassol.com` |

### Escola Horizonte

| Perfil | E-mail |
|---|---|
| Coordenação | `coordenacao@horizonte.com` |
| Professor | `professora@horizonte.com` |
| Marketing | `marketing@horizonte.com` |

### Contas familiares para o TinhaKids

| Escola | E-mail | Aluno acessível |
|---|---|---|
| Girassol | `pai.teste@girassol.com` | FILHO TESTE |
| Girassol | `mae.sofia@girassol.com` | Sofia |
| Horizonte | `pai.teste@horizonte.com` | Pedro |
| Horizonte | `mae.sofia@horizonte.com` | Sofia |

O TinhaKids usa somente os vínculos e conteúdos reais do Prisma. Não existe mais entrada automática com dados fictícios quando o login falha. As imagens do seed são cartões de demonstração, não fotos reais de alunos.

## 5. Testes do perfil Coordenação

Entre no Prisma com `coordenacao@girassol.com` e `mypassword`.

### 5.1 Visão geral

- [ ] O login direciona para `/admin`.
- [ ] O nome exibido é Escola Girassol.
- [ ] São mostradas quantidades de profissionais, turmas, crianças e fotos.
- [ ] O armazenamento apresenta o espaço realmente usado pelas fotos registradas.
- [ ] O botão **Conhecer upgrades** abre apenas uma mensagem informativa.
- [ ] Nenhuma cobrança ou limite de upload é aplicado.

### 5.2 Profissionais

- [ ] Abra **Profissionais**.
- [ ] Cadastre um Professor com nome, e-mail e senha inicial.
- [ ] Vincule o Professor a uma ou mais turmas.
- [ ] Cadastre um usuário de Marketing.
- [ ] Confirme que não existe opção para cadastrar outro Coordenador.
- [ ] Edite nome, e-mail ou turmas do Professor.
- [ ] Informe uma nova senha e confirme que o login antigo deixa de funcionar.
- [ ] Desative um profissional e confirme que ele não consegue entrar.
- [ ] Reative o profissional e confirme que o login volta a funcionar.
- [ ] Filtre por turma ou **Sem turma**.
- [ ] Use **Mostrar/Ocultar desativados** e confirme os resultados.

### 5.3 Turmas

- [ ] Abra **Turmas**.
- [ ] Cadastre uma nova turma com nome e ano letivo.
- [ ] Atribua um Professor à turma.
- [ ] Edite o nome, o ano ou os Professores responsáveis.
- [ ] Clique em **Abrir fotos** e confirme que a galeria da turma é exibida.
- [ ] Desative a turma e confirme que o histórico não é apagado.
- [ ] Reative a turma.
- [ ] Filtre uma turma específica ou **Sem professores**.
- [ ] Use **Mostrar/Ocultar desativados**.

### 5.4 Alunos

- [ ] Abra **Alunos** e filtre por turma.
- [ ] Clique em **Cadastrar** e cadastre um aluno pelo modal, com nenhum, um ou vários familiares.
- [ ] Confirme a mensagem de sucesso após salvar.
- [ ] Marque ou desmarque a autorização para Marketing.
- [ ] Edite o nome da criança.
- [ ] Transfira a criança para outra turma.
- [ ] Desative a criança e confirme que o cadastro continua no histórico.
- [ ] Reative a criança.
- [ ] Use **Mostrar/Ocultar desativados**.
- [ ] Clique em **Ver fotos** e confirme que a página de fotos abre filtrada pelo aluno.
- [ ] Abra uma turma e confirme que o cartão **Alunos** substitui o antigo cartão de vínculos familiares.

### 5.5 Biblioteca geral de fotos

Abra <http://localhost:3000/admin/photos> ou use o item **Fotos** do menu.

- [ ] A página mostra fotos de todas as turmas da Escola Girassol.
- [ ] O filtro de turma reduz corretamente os resultados.
- [ ] O filtro de situação diferencia pendentes, privadas e aprovadas.
- [ ] A busca encontra fotos por título, descrição, autor ou turma.
- [ ] **Abrir turma** leva para a galeria correta.
- [ ] **Baixar** abre ou salva a imagem.
- [ ] Alterar a liberação para **Aprovada para marketing** faz a foto aparecer para o perfil Marketing.
- [ ] Alterar para **Somente escola** remove a foto da área de Marketing.

### 5.6 Fila de processamento e reconhecimento facial

Entre como Coordenador e abra **Fila facial** no menu do painel ou acesse <http://localhost:3000/admin/processing>.

1. Confirme que o worker está rodando. O inicializador do Windows abre uma janela para ele; no modo manual, use o Terminal 2 da seção 3.
2. Coloque arquivos de imagem ou um arquivo `.zip` em `prisma/backend/test_images/`. O repositório inclui `Imagens guri.zip` para esse fluxo.
3. Clique em **Importar Pasta de Testes**. A API extrai arquivos ZIP automaticamente, percorre as subpastas e importa imagens compatíveis para a fila. Faça essa importação uma vez por conjunto de imagens para evitar cadastrar fotos repetidas.
4. Aguarde o worker ou clique em **Iniciar Processamento Agora**. A lista deve mostrar os estados **Pendente**, **Processando**, **Concluído** ou **Falhou**.

- [ ] A contagem da fila aumenta após a importação.
- [ ] Fotos processadas mostram recortes de faces e grupos encontrados.
- [ ] Clicar em um grupo filtra as fotos relacionadas; limpar o filtro restaura a lista.
- [ ] Uma foto inexistente ou inválida fica como **Falhou** e mostra o erro registrado.
- [ ] **Reprocessar Falhas** recoloca fotos com erro na fila.
- [ ] **Reagrupar Faces** atualiza os grupos a partir das faces já detectadas.
- [ ] A fila e os grupos mostram somente fotos da escola do coordenador autenticado.
- [ ] Ao entrar com a outra escola, nenhuma foto, recorte ou grupo da primeira aparece.
- [ ] **Reprocessar Falhas**, **Reprocessar Todas** e **Reagrupar Faces** alteram somente a escola atual.
- [ ] Professores, marketing e familiares não conseguem consultar ou alterar a fila e os grupos pela API.
- [ ] Consultas sem login são recusadas, inclusive no antigo endereço direto de recortes.
- [ ] Os recortes exibidos na tela usam URLs assinadas temporárias; uma assinatura adulterada ou expirada é recusada.

**Limite do detector:** o `Pipfile` atual não instala InsightFace. Se InsightFace e seus modelos não estiverem disponíveis no ambiente, o worker usa um detector de fallback; nesse caso, o roteiro valida a importação, a fila e a tela, mas não a precisão do reconhecimento real.

### 5.7 Familiares e vínculo com o TinhaKids

1. Entre como Coordenação e abra a aba **Familiares** do painel.
2. Clique em **Cadastrar**, informe nome, e-mail e senha inicial e selecione os alunos desse familiar.
3. Também é possível cadastrar primeiro o familiar sem alunos e selecioná-lo ao cadastrar ou editar um aluno na aba **Alunos**.
4. Para um novo teste, use uma conta diferente das já criadas pelo seed, por exemplo:

```text
Nome: Responsável Teste
E-mail: teste@teste.com
Senha inicial: 123456
```

- [ ] O vínculo é salvo e a mensagem de sucesso aparece.
- [ ] O responsável entra no TinhaKids com o mesmo e-mail e senha cadastrados no Prisma.
- [ ] Somente os alunos selecionados aparecem no TinhaKids.
- [ ] Somente publicações e portfólios destinados a esses alunos aparecem. Um upload ou reconhecimento facial sozinho não publica uma foto para as famílias.
- [ ] Alterar o nome ou a turma da criança pelo painel atualiza o perfil familiar correspondente.
- [ ] Remova um vínculo no Prisma e puxe a tela de publicações do TinhaKids para atualizar: o aluno e suas fotos desaparecem dessa conta.
- [ ] Vincule novamente o mesmo aluno: o histórico publicado volta a aparecer sem duplicar o aluno.
- [ ] Vincule dois familiares ao mesmo aluno: ambos podem acessar o conteúdo desse aluno.
- [ ] Desative um familiar: ele não pode entrar nem consultar a API com uma sessão antiga.
- [ ] Redefina a senha manualmente e confirme o novo login.
- [ ] Use **Mostrar/Ocultar desativados** e reative o familiar.

## 6. Testes do perfil Professor

Entre no Prisma com `professora@girassol.com` e `mypassword`.

- [ ] O login direciona para a página **Minhas turmas**.
- [ ] São exibidas somente as turmas atribuídas ao Professor.
- [ ] O Professor consegue abrir a galeria de uma turma atribuída.
- [ ] O Professor não vê a seção **Vínculos familiares**.
- [ ] O Professor não consegue acessar `/admin` ou `/admin/photos`.
- [ ] O Professor não consegue usar a API de vínculos familiares; a API deve responder `403`.
- [ ] Uma turma não atribuída não pode ser aberta pelo Professor.
- [ ] O Professor consegue criar publicações e portfólios usando crianças que já possuem vínculo familiar.

## 7. Testes do perfil Marketing

Entre no Prisma com `marketing@girassol.com` e `mypassword`.

- [ ] O login direciona para `/marketing`.
- [ ] A página mostra somente fotos aprovadas para Marketing.
- [ ] Fotos pendentes ou marcadas como **Somente escola** não aparecem.
- [ ] A busca encontra fotos por título, descrição ou autor.
- [ ] O download da imagem funciona.
- [ ] O perfil não consegue acessar turmas, crianças, vínculos familiares ou `/admin`.

## 8. Teste de isolamento entre escolas

Esse teste é obrigatório sempre que uma nova API de cadastro ou consulta for criada.

1. Entre como Coordenação da Escola Girassol.
2. Anote as turmas, crianças, profissionais e fotos exibidos.
3. Saia e entre como Coordenação da Escola Horizonte.
4. Compare os dados.

- [ ] A Escola Horizonte não mostra dados da Escola Girassol.
- [ ] A Escola Girassol não mostra dados da Escola Horizonte.
- [ ] Alterar manualmente um ID na URL não permite abrir registros de outra escola.
- [ ] IDs de outra escola são tratados como registros inexistentes.
- [ ] Marketing vê somente fotos aprovadas da própria escola.
- [ ] Professor vê somente turmas da própria escola às quais foi atribuído.

## 9. Configurar e testar o TinhaPhone

O Prisma precisa estar rodando antes de abrir o TinhaPhone.

### 9.1 Endereço da API

Use o endereço correspondente ao dispositivo:

| Ambiente | Endereço |
|---|---|
| Emulador Android | `http://10.0.2.2:8000` |
| iOS Simulator ou aplicativo desktop | `http://127.0.0.1:8000` |
| Celular físico | `http://IP-DO-COMPUTADOR:8000` |

Para celular físico, computador e celular devem estar na mesma rede. Descubra o IP do computador com:

```powershell
ipconfig
```

### 9.2 Iniciar

Confira os dispositivos disponíveis:

```powershell
flutter devices
```

Depois execute:

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\tinhaphone
flutter pub get
flutter run
```

### 9.3 Configuração no aplicativo

Na tela de configuração do TinhaPhone, informe:

- Endereço da API conforme a tabela anterior.
- E-mail do Professor, por exemplo `professora@girassol.com`.
- Senha `mypassword`.
- ID de uma turma atribuída ao Professor.

Para descobrir o ID da turma:

1. Entre como Professor ou Coordenador no Prisma.
2. Abra a turma desejada.
3. Observe o número no final da URL. Exemplo: `/class/1` significa ID `1`.

Não fixe o ID no teste: ele pode mudar quando o banco for recriado.

### 9.4 Envio de foto

- [ ] Use **Testar conexão** e confirme que o nome das turmas é apresentado.
- [ ] Salve a configuração.
- [ ] Tire uma foto.
- [ ] Confirme que o aplicativo informa **Foto enviada ao Prisma com sucesso**.
- [ ] Abra a turma no Prisma e confirme que a foto apareceu.
- [ ] Abra a biblioteca geral da Coordenação e confirme que a mesma foto aparece.
- [ ] Confirme que a foto nova começa como **Aguardando revisão**.
- [ ] Desligue temporariamente o backend, tente enviar e confirme que o erro fica registrado.
- [ ] Ligue o backend novamente e use a opção de tentar o upload outra vez.

### 9.5 Limpeza automática do aparelho

Use fotos de teste. A opção vem **desligada** e só remove cópias privadas do TinhaPhone cujo envio foi confirmado pelo Prisma. Os originais do rolo da câmera não são apagados.

- [ ] Com a opção desligada, envie uma foto e confirme que continua na galeria do TinhaPhone.
- [ ] Abra **Configurações**, marque **Apagar automaticamente fotos sincronizadas** e toque em **Salvar**.
- [ ] Volte à tela inicial e confirme que as cópias já enviadas desapareceram do TinhaPhone, mas continuam no Prisma.
- [ ] Tire outra foto: depois do envio confirmado, a cópia local deve desaparecer sem deixar miniatura quebrada na câmera.
- [ ] Com a API indisponível ou o celular sem rede, tire uma foto. Ela deve permanecer no aparelho como pendente/erro, mesmo com a limpeza ativa.
- [ ] Restabeleça a conexão e toque em **Enviar**. Confirme a presença no Prisma antes de considerar o teste aprovado.
- [ ] Feche e reabra o app; confira que a escolha da limpeza continua salva.
- [ ] Desmarque a opção e salve. Novos envios devem voltar a preservar a cópia local.

Fotos antigas sincronizadas apenas com o Google Drive, sem confirmação do Prisma, não são removidas por esta limpeza.

### 9.6 Compartilhar fotos da galeria com o TinhaPhone

É necessário recompilar e reinstalar/atualizar o aplicativo; um hot reload não atualiza o menu de compartilhamento do sistema. Estes testes são para Android/iPhone, não para navegador ou Windows. No iPhone, a compilação e validação exigem macOS/Xcode.

- [ ] Configure o acesso e confira o código da turma que receberá as imagens.
- [ ] Na galeria do celular, selecione uma imagem e use **Compartilhar → Tinhaphone**.
- [ ] Confirme o recebimento no aplicativo e o envio para a **turma configurada** no Prisma.
- [ ] Repita com várias imagens selecionadas: todas devem aparecer no Prisma.
- [ ] Repita com o TinhaPhone completamente fechado e depois com ele já aberto.
- [ ] Compartilhe sem rede: as cópias devem ficar salvas no app para usar **Enviar** depois.
- [ ] Em uma instalação sem configuração, compartilhe uma imagem, volte da configuração sem salvar e confira que ela fica pendente. Configure o Prisma depois e toque em **Enviar**.
- [ ] Com a limpeza automática ativa, confirme que a cópia do TinhaPhone desaparece após o envio, mas a foto **original continua na galeria do celular**.
- [ ] Ao reabrir o app normalmente, confirme que ele não importa novamente o último compartilhamento.
- [ ] Verifique que o TinhaPhone aparece para imagens, não para compartilhar textos ou vídeos.

## 10. Criar conteúdo para o TinhaKids

Antes deste teste:

- A criança deve possuir vínculo familiar.
- Deve existir ao menos uma foto na turma.

### Publicação para o feed

1. Abra a galeria da turma no Prisma.
2. Selecione uma foto ou use **Selecionar várias**.
3. Clique em **Publicar**.
4. Escreva a legenda.
5. Marque uma criança que já possui vínculo familiar.
6. Confirme a publicação.

- [ ] A publicação aparece em **Publicações recentes**.
- [ ] Somente responsáveis vinculados à criança conseguem visualizá-la.

### Portfólio

1. Selecione uma ou mais fotos.
2. Clique em **Portfólio**.
3. Informe título, descrição e objetivos pedagógicos.
4. Selecione uma criança com vínculo familiar.
5. Confirme.

- [ ] O portfólio é criado para a criança selecionada.
- [ ] Várias fotos são preservadas como uma galeria do mesmo projeto.

## 11. Iniciar e testar o TinhaKids

Para testar no navegador:

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\tinhakids
flutter pub get
flutter run -d chrome
```

Para Android, use um dispositivo listado em `flutter devices`:

```powershell
flutter run -d ID-DO-DISPOSITIVO
```

Para conferir o exemplo real criado pelo seed no TinhaKids, use:

```text
E-mail: pai.teste@girassol.com
Senha: mypassword
```

Essa conta mostra somente **FILHO TESTE**. Saia e entre com `mae.sofia@girassol.com` / `mypassword`: somente **Sofia** deve aparecer, com outra publicação e outro portfólio.

Todas as contas dependem da API do Prisma em execução. Para celular físico, use `flutter run -d ID-DO-DISPOSITIVO --dart-define=API_URL=http://IP-DO-COMPUTADOR:8000`. Uma conta nova usa o e-mail e a senha definidos pela Coordenação na aba **Familiares**. O app nunca substitui um erro de login por dados locais fictícios.

### Feed

- [ ] A criança vinculada aparece após o login.
- [ ] A publicação criada no Prisma aparece no feed.
- [ ] A legenda, o Professor e as imagens estão corretos.
- [ ] Uma publicação com várias fotos permite visualizar todas elas.
- [ ] Conteúdos de outras crianças ou escolas não aparecem.

### Portfólio

- [ ] O projeto criado no Prisma aparece na aba **Portfólio**.
- [ ] Título, descrição, data e objetivos pedagógicos estão corretos.
- [ ] Todas as fotos do projeto aparecem.

### Perfil

- [ ] Nome e turma da criança estão atualizados.
- [ ] O histórico de fotos é exibido.
- [ ] Os filtros disponíveis funcionam.
- [ ] Sair remove a sessão e retorna para a tela de login.

## 12. Roteiro completo de teste integrado

Use esta sequência para validar os três aplicativos de ponta a ponta:

1. [ ] Inicie Docker, backend e frontend do Prisma.
2. [ ] Entre como Coordenação da Escola Girassol.
3. [ ] Confirme profissionais, turma e crianças do seed.
4. [ ] Abra **Familiares** e confira o vínculo de `pai.teste@girassol.com` com FILHO TESTE. Para testar cadastro, crie outro familiar por essa aba e selecione o aluno.
5. [ ] Configure o TinhaPhone com o Professor e o ID dessa turma.
6. [ ] Tire e envie uma nova foto pelo TinhaPhone.
7. [ ] Confirme a foto na biblioteca geral da Coordenação.
8. [ ] Abra a turma e crie uma publicação para a criança vinculada.
9. [ ] Crie também um item de portfólio.
10. [ ] Entre no TinhaKids como `pai.teste@girassol.com` / `mypassword` e valide feed e portfólio; as fotos de Sofia não devem aparecer. Depois confira Sofia usando `mae.sofia@girassol.com`.
11. [ ] Volte à Coordenação e aprove a foto para Marketing.
12. [ ] Entre como Marketing e confirme que a foto aparece.
13. [ ] Mude a foto para **Somente escola** e confirme que ela desaparece do Marketing.
14. [ ] Entre como Professor e confirme que vínculos familiares não são exibidos.
15. [ ] Repita consultas básicas com a Escola Horizonte para validar o isolamento.

## 13. Testes automatizados

### Backend Prisma

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\prisma\backend
$env:DATABASE_URL = "sqlite:///:memory:"
pipenv run python -m unittest discover -s tests -v
Remove-Item Env:DATABASE_URL
```

Os testes cobrem:

- Isolamento entre escolas.
- Permissões dos três perfis.
- Restrições do Coordenador ao criar profissionais.
- Listagem consolidada de fotos.
- Marketing recebendo somente fotos aprovadas.
- Assinaturas expiradas de imagens.
- Publicações para famílias.
- Portfólios com várias fotos.
- Criação e vínculo de conta familiar.
- Login real do familiar criado no Prisma e acesso somente aos conteúdos dos alunos vinculados.
- Remoção e restauração de vínculo sem perder o histórico publicado.
- Bloqueio de conta familiar, aluno ou escola inativos.

Os testes usam somente SQLite em memória e possuem proteção contra alterações no PostgreSQL local. Execute os comandos de testes em um terminal separado da API.

O conjunto automatizado também cobre autenticação e permissões da fila e dos grupos, contagens e fotos por escola, recortes assinados, processamento e re-enfileiramento restritos à escola, agrupamento de embeddings iguais em escolas diferentes sem misturá-las e preservação da outra escola ao reagrupar. A precisão do detector facial real ainda exige validação manual com o InsightFace instalado.

As migrações de segurança restauram `Parent.updated_at` e a identificação Google única, além de identificar a escola dos grupos antigos sem apagar fotos ou faces. Se houver identificações Google duplicadas, a atualização interrompe com um aviso para revisão, sem excluir contas automaticamente. Grupos antigos sem escola identificável são preservados, mas não ficam disponíveis no painel até terem uma escola definida.

### Frontend Prisma

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\prisma\frontend
npm run lint
npm run build
```

### TinhaPhone

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\tinhaphone
flutter analyze
flutter test
```

### TinhaKids

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\tinhakids
flutter analyze
flutter test
```

No TinhaKids também são testados: ausência de login fictício, descarte de sessão antiga de demonstração, atualização dos vínculos, troca rápida entre alunos sem mistura de fotos, saída com requisição pendente e limpeza de conteúdo após erro de acesso.

## 14. Registro dos resultados

Para cada rodada, registre:

| Informação | Valor |
|---|---|
| Data do teste | |
| Responsável pelo teste | |
| Versão ou commit | |
| Dispositivo do TinhaPhone | |
| Dispositivo do TinhaKids | |
| Escola utilizada | |
| Resultado geral | Aprovado / Reprovado |

Para cada falha, anote:

- Perfil utilizado.
- Escola utilizada.
- Passos realizados.
- Resultado esperado.
- Resultado encontrado.
- Mensagem de erro.
- Captura de tela, quando possível.

## 15. Diagnóstico rápido

### O portal não abre

- Confirme que `npm run dev` está rodando.
- Acesse <http://localhost:3000>.
- Verifique se a porta 3000 não está ocupada por outro programa.

### A API não responde

- Acesse <http://localhost:8000/docs>.
- Confirme que o backend foi iniciado com `pipenv run uvicorn app.main:app --reload`.
- Confirme que o PostgreSQL está ativo com `docker compose ps`.

### O emulador Android não encontra a API

- Use `http://10.0.2.2:8000`, nunca `localhost`.
- Confirme que o backend está aceitando conexões.

### O celular físico não encontra a API

- Use o IP local do computador.
- Verifique se os dois aparelhos estão na mesma rede.
- Libere a porta 8000 no firewall apenas para a rede local de desenvolvimento.

### O TinhaKids não aceita a conta familiar

- Depois de um seed novo, use `pai.teste@girassol.com` e `mypassword` para o exemplo FILHO TESTE.
- Para uma conta criada manualmente, use o e-mail e a senha definidos pela Coordenação na aba **Familiares**.
- Não existe mais um login offline com `teste@teste.com`: esse e-mail só funciona se cadastrado no Prisma com uma senha válida.
- Confirme que a conta real está vinculada à criança correta.

### A publicação não aparece no TinhaKids

- Confirme que a publicação foi associada à criança correta.
- Confirme que a criança possui perfil familiar.
- Atualize o aplicativo ou entre novamente.

### A foto não aparece para Marketing

- Confirme que a situação é **Aprovada para marketing**.
- Confirme que o usuário de Marketing pertence à mesma escola da foto.

### A fila facial não processa as fotos

- Confirme que a janela do worker está aberta ou inicie `pipenv run python worker.py --interval 3` na pasta `prisma/backend`.
- Confira se as imagens estão em `prisma/backend/test_images/` e se têm uma extensão compatível.
- Abra **Fila facial** e veja se há mensagens de erro nas fotos marcadas como **Falhou**.
- A API aplica automaticamente a migração aditiva das colunas da fila. Não rode `-Seed` para corrigir erros de banco, pois ele apaga os dados locais.
- Se o erro de coluna ausente persistir, confira a saída da janela do backend e confirme que API e worker foram reiniciados.
