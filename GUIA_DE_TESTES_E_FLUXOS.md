# Guia de testes e fluxos dos aplicativos

> Unificação validada em 17/10/2026: 45 testes de backend, 36 testes do app unificado e um teste integrado Android passaram. Os 11 testes do projeto familiar antigo também passaram. APK de desenvolvimento compilado. iPhone e compartilhamento pelo menu externo do sistema continuam com validação manual pendente; no teste integrado, a entrega do compartilhamento é simulada no limite do plugin.

Este documento descreve como iniciar e testar o ecossistema formado por:

- **Prisma:** portal web e API da escola.
- **TinhaKids unificado:** um aplicativo para professores e familiares, desenvolvido na pasta `tinhaphone`.
- **tinhakids (repositório antigo):** referência histórica; não é o app atual.

## 1. Visão geral do fluxo

```text
Coordenação cadastra profissionais, turmas e crianças no Prisma
                              ↓
Professor entra no TinhaKids e escolhe uma de suas turmas
                              ↓
Professor tira uma foto e o TinhaKids envia para o Prisma
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

## 9. Iniciar o TinhaKids unificado e testar a área do professor

O código do aplicativo único está na pasta **tinhaphone**. Não é necessário instalar um segundo app para a família. Não execute o seed para atualizar: os cadastros e vínculos do Prisma permanecem existentes.

### 9.1 Executar no Android

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\tinhaphone
flutter pub get
flutter devices
flutter run -d ID-DO-DISPOSITIVO
```

No emulador Android, a API padrão é `http://10.0.2.2:8000`. No celular físico, utilize o IP do computador:

```powershell
flutter run -d ID-DO-DISPOSITIVO --dart-define=API_URL=http://IP-DO-COMPUTADOR:8000
```

A tela de login possui **Servidor de testes** para alterar o endereço sem recompilar. A senha não é salva: somente a sessão fica no armazenamento seguro do dispositivo.

**Preservação:** não desinstale o aplicativo nem use `flutter install` para atualizar uma instalação com dados. Esse comando pode remover a versão anterior. Para instalar um APK já compilado mantendo os dados, utilize `adb install -r caminho-do-apk`; se houver erro de assinatura, interrompa e faça backup, sem desinstalar. O identificador normal continua `com.example.tinhaphone`.

### 9.2 Entrada e escolha de turma

- [ ] Na tela **TinhaKids**, entre com uma conta de Professor existente no Prisma.
- [ ] Confirme a área **Câmera escolar**, sem telas de familiares.
- [ ] Selecione a turma pelo nome. Somente turmas atribuídas ao professor devem aparecer.
- [ ] Com um professor sem turmas, confira a mensagem de orientação e o bloqueio da câmera/importação.
- [ ] Tente credenciais inválidas, conta inativa, Coordenação e Marketing; nenhum deve entrar.
- [ ] Confira que não é necessário informar usuário, senha ou código numérico nas configurações.
- [ ] Cada e-mail só pode pertencer a uma conta. Quem for professor e familiar precisa de e-mails diferentes.

### 9.3 Captura, fila e troca de conta

- [ ] Tire uma foto e confira a confirmação de envio e sua presença na turma correta do Prisma.
- [ ] Sem rede, capture outra foto. Ela deve permanecer salva para tentar novamente.
- [ ] Troque a turma selecionada: fotos já pendentes mantêm a turma em que foram criadas.
- [ ] Durante um envio, o botão **Sair** e a troca de turma ficam indisponíveis.
- [ ] Saia e entre com outro professor: fotos, turmas, configurações e registros de erro da conta anterior não devem aparecer.
- [ ] Volte à primeira conta e confira sua fila anterior.
- [ ] Reabra o app: a sessão deve ser validada pelo servidor; sessão expirada exige login sem apagar a fila.
- [ ] Sem conexão ao reabrir, o app pede nova autenticação; os arquivos pendentes permanecem preservados.
- [ ] A fila começa nova. Fotos antigas de `photo_vault.db` não são importadas nem apagadas pelo aplicativo unificado.

### 9.4 Limpeza e compartilhamento

- [ ] Nas configurações, ative **Apagar automaticamente fotos sincronizadas** e salve.
- [ ] Confira a remoção apenas das cópias desta conta confirmadas pelo Prisma.
- [ ] Pendências e originais da galeria devem permanecer intactos.
- [ ] Com professor autenticado e turma selecionada, use **Compartilhar → TinhaKids** na galeria.
- [ ] Teste uma e várias imagens, com o app aberto e fechado, e também sem rede.
- [ ] Sem turma selecionada, confira o aviso para escolher uma turma e compartilhar novamente, sem envio nem remoção do original.
- [ ] Com uma sessão familiar, compartilhe uma imagem: não deve haver importação ou upload.
- [ ] Ao retornar a uma conta de professor depois de sair da família, a imagem descartada não deve ser enviada.
- [ ] O último compartilhamento não pode ser importado repetidamente ao reabrir o app.

### 9.5 iPhone — checklist pendente de macOS/Xcode

O nome, os identificadores existentes, o grupo da extensão de compartilhamento e o armazenamento seguro foram preparados para iOS. Compilação, assinatura e comportamento em iPhone **não foram validados neste Windows**.

Em um Mac, executar `flutter pub get` e `flutter build ios --no-codesign`, configurar assinatura do Runner e da ShareExtension no Xcode e repetir os testes de login, restauração do token, câmera, envio, compartilhamento aberto/fechado e limpeza. Usar um servidor acessível ao iPhone. Validar acesso negado às permissões sem travamento, manutenção dos originais e ausência de envio na área familiar.

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

## 11. Testar a área familiar no mesmo TinhaKids

Use a mesma instalação da seção 9. Saia da conta de professor e entre com o e-mail e senha de um familiar cadastrado no Prisma. Não é necessário instalar ou executar o projeto antigo da pasta `tinhakids`.

Contas de desenvolvimento do seed (somente se já existirem na base):
- `pai.teste@girassol.com` / `mypassword`: somente FILHO TESTE.
- `mae.sofia@girassol.com` / `mypassword`: somente Sofia.

- [ ] O familiar entra diretamente na **Área da família**, sem câmera, seleção de turma ou fila.
- [ ] Familiar sem alunos vinculados recebe orientação para consultar a escola, sem falhar no login.
- [ ] A alteração/remoção de vínculos no Prisma é refletida ao atualizar.
- [ ] Sair limpa as telas. Voltar ou uma resposta de rede atrasada não pode reabrir os dados da conta anterior.

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

Use esta sequência para validar o portal e as duas áreas do aplicativo único:

1. [ ] Inicie Docker, backend e frontend do Prisma.
2. [ ] Entre como Coordenação da Escola Girassol.
3. [ ] Confirme profissionais, turma e crianças do seed.
4. [ ] Abra **Familiares** e confira o vínculo de `pai.teste@girassol.com` com FILHO TESTE. Para testar cadastro, crie outro familiar por essa aba e selecione o aluno.
5. [ ] Entre no TinhaKids como Professor e selecione essa turma pelo nome.
6. [ ] Tire e envie uma nova foto pelo TinhaKids.
7. [ ] Confirme a foto na biblioteca geral da Coordenação.
8. [ ] Abra a turma e crie uma publicação para a criança vinculada.
9. [ ] Crie também um item de portfólio.
10. [ ] Saia do Professor no mesmo app, entre como `pai.teste@girassol.com` / `mypassword` e valide feed e portfólio; as fotos de Sofia não devem aparecer. Depois confira Sofia usando `mae.sofia@girassol.com`.
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

### Aplicativo unificado

```powershell
cd C:\Users\Guilherme\Desktop\JavaScript_Projects\jorge\tinhaphone
flutter analyze --no-fatal-infos
flutter test
flutter build apk --debug
```

O conjunto inclui os testes familiares portados, armazenamento, configurações por conta, sessão, isolamento de filas e telas vazias/erros. O analisador ainda informa avisos antigos da câmera; não há erros ou warnings de análise.

### Integração Android com o Prisma real

Use um emulador de testes, API iniciada e as contas acima existentes, sem executar seed sobre sua base.

```powershell
flutter test integration_test/unified_app_test.dart -d ID-DO-EMULADOR --no-uninstall
```

O Android usa automaticamente o pacote separado `com.example.tinhaphone.integration` para alvos da pasta `integration_test`. O runner pode removê-lo ao terminar, sem remover a instalação normal ou seus arquivos. É necessário permitir a câmera no aplicativo de teste.

O teste cobre armazenamento seguro nativo, login/validação reais, turma, captura e envio reais, limpeza, logout e área familiar. O recebimento do compartilhamento é simulado no limite do plugin; o menu externo do sistema ainda deve ser conferido manualmente. O teste cria duas fotos no Prisma e não exclui os registros do servidor. Pode usar `--dart-define=TEST_TEACHER=...`, `TEST_FAMILY` e `TEST_PASSWORD` para outras contas de desenvolvimento.

### Projeto familiar antigo

O repositório `tinhakids` permanece como referência, sem alteração nesta unificação. Seus testes podem ser executados separadamente com `flutter test`, mas não substituem os testes do aplicativo único.

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

## Gestão de publicações — incremento de 27/10/2026

### Preparação e preservação de dados

- Reinicie a API para aplicar a migração incremental; não execute seed nem recrie o banco.
- A migração acrescenta turma, autoria da conta e ordem das fotos; recupera a turma antiga somente quando identificável e reconcilia fotos antigas por caminho dentro da mesma escola.
- Publicações antigas mantêm autor, conteúdo, fotos e famílias. Como não possuem autoria de conta comprovada, professores só podem visualizá-las; a coordenação pode editar e excluir.
- Quando uma publicação antiga estiver sem turma identificável, apenas a coordenação a verá. Ao editar, deverá selecionar a turma e revisar fotos/alunos para regularizar os vínculos.

### Professor — checklist de tela

- [ ] Na página inicial, abrir **Publicações**; na turma, testar **Gerenciar publicações** e conferir o filtro da turma.
- [ ] Buscar pela legenda e combinar com o filtro de turma. Testar sem publicações e sem resultados.
- [ ] Abrir **Nova publicação**, selecionar uma turma, marcar várias fotos, ampliar as imagens e conferir a indicação de capa.
- [ ] Selecionar os alunos destinatários e preencher a legenda. Alunos sem perfil familiar ficam indisponíveis, com orientação para procurar a coordenação.
- [ ] Conferir os destinatários antes de publicar. Durante o salvamento, o botão e o fechamento ficam bloqueados; deve aparecer confirmação de sucesso.
- [ ] Abrir **Ver publicação** e conferir todas as fotos, legenda, autor, turma e alunos.
- [ ] Editar uma publicação recém-criada: trocar legenda, fotos e alunos, sem trocar a turma. A data e a autoria originais devem ser preservadas.
- [ ] Publicações de colegas e antigas abrem normalmente; seus menus não oferecem edição/exclusão. Não há aviso repetitivo de somente leitura na lista.
- [ ] Excluir uma publicação criada para este teste. Confirmar o aviso de remoção das famílias e preservação das fotos; cancelar antes para validar ambos os caminhos.
- [ ] Testar Escape, navegação por teclado, tela estreita, carregamento e falha de rede. Uma imagem indisponível não deve remover o registro; o visualizador oferece nova tentativa.

### Fotos e famílias

- [ ] Na biblioteca da turma, conferir o selo **Em publicação** e a quantidade de usos nos detalhes da foto.
- [ ] Na biblioteca geral da coordenação, conferir o mesmo selo, contagem e filtros.
- [ ] Combinar **Em publicação / Não utilizadas** com filtros de turma, aluno, tags ou datas disponíveis em cada página.
- [ ] Usar a mesma foto em duas publicações de teste. A contagem deve ser 2; excluir uma deve manter o selo e contagem 1.
- [ ] Remover a foto da última publicação ou excluir essa publicação: o selo desaparece e a foto permanece na biblioteca, com tags e portfólios preservados.
- [ ] Atualizar o TinhaKids familiar: conferir a criação e as alterações. O aluno removido deixa de receber a publicação; o aluno adicionado passa a recebê-la.
- [ ] Após excluir a publicação, atualizar o feed familiar e confirmar sua ausência. Arquivos já baixados pela família não são apagados do celular.

### Coordenação e permissões

- [ ] Abrir **Publicações** pelo painel da coordenação e administrar as publicações de sua escola, inclusive antigas e de outros autores.
- [ ] Professor de outra turma não deve conseguir abrir a publicação por URL/API. Nenhum usuário deve acessar conteúdo de outra escola.
- [ ] Marketing não acessa a página nem seus endpoints administrativos.
- [ ] Na edição, alunos que saíram da turma ou fotos indisponíveis exigem revisão explícita da seleção, sem remoção silenciosa.

### Validações executadas nesta entrega

- Backend: `pipenv run python -W ignore::DeprecationWarning -m unittest discover -s tests` — **60 testes passaram**, incluindo 11 novos testes de gestão/migração.
- Novos testes cobrem autoria, publicações antigas, turmas renomeadas, isolamento de escolas, troca de destinatários, preservação de ordem/capa/data, contagens sem consultas individuais e exclusão sem apagar fotos/portfólios.
- Frontend: lint sem erros (cinco avisos anteriores na fila facial), verificação TypeScript e build de produção.
- PostgreSQL local: migração aplicada sem seed, com cópia de segurança prévia; publicações antigas permaneceram sem autoria atribuída automaticamente.
- API real: criação, edição, autoria, contagem de uso e leitura no feed familiar validadas com publicação temporária; ela foi removida ao terminar, preservando a foto e sua contagem original.
- **Pendente:** executar o checklist visual acima no navegador. A automação de navegador não conseguiu estabelecer a conexão de depuração neste ambiente; não foi possível declarar esses testes visuais como concluídos.
- Fora do MVP: arquivamento, restauração, rascunhos, agendamento, notificações e histórico de versões.

## Publicações — reformulação da interface web (30/10/2026)

### Conferência no portal

- [ ] Abrir `/publications` como professor. Conferir nome da escola, profissional e navegação com Publicações ativa; coordenação mantém o acesso ao painel.
- [ ] Conferir botão Nova publicação.
- [ ] Buscar por legenda, professor, turma ou aluno; combinar com turma e data. Conferir o total abaixo da barra.
- [ ] Testar Hoje, Últimos 7 dias, Este mês e Período personalizado. Datas inicial e final inclusivas no fuso local; intervalo invertido mostra orientação.
- [ ] Ordenar por Mais recentes e Mais antigas. Limpar filtros retorna à lista geral e ordem padrão.
- [ ] Conferir capas uniformes, contagem de múltiplas fotos, legenda limitada a duas linhas, autor, turma, data e alunos.
- [ ] Clicar numa linha: abre drawer à direita no desktop e tela cheia no celular, com destaque da linha ativa.
- [ ] Navegar por todas as fotos; conferir indicador de posição, proporção sem cortes e ampliação. Fechar a ampliação retorna à mesma foto.
- [ ] Conferir legenda completa com parágrafos e destinatários. Fechar detalhes deve manter busca, turma, data, ordem, lote carregado e rolagem da lista.
- [ ] Abrir três pontos sem abrir detalhes. Testar Enter, setas, Home/End, Escape e clique fora. Editar/Excluir aparecem apenas quando permitidos pelo servidor.
- [ ] Editar/excluir pelos menus da lista e do drawer; cancelar e confirmar. A turma continua fixa na edição e a exclusão não apaga fotos.
- [ ] Criar uma publicação e conferir confirmação; o aplicativo familiar continua recebendo pelo fluxo existente.
- [ ] Com mais de 25 publicações, testar Carregar mais. Alterar um filtro reinicia a quantidade exibida, mantendo a contagem total correta.
- [ ] Testar lista vazia, nenhum resultado, falha inicial e nova tentativa, falha nos detalhes e imagens indisponíveis. Fechar durante uma requisição não deve reabrir o painel com resposta atrasada.
- [ ] Conferir larguras 320, 390, 768 e 1280 px: sem rolagem horizontal, legenda truncada só na lista e controles acessíveis. Testar foco nativo dos dialogs e retorno ao botão de origem.

### Validação automatizada desta reformulação

- `frontend`: `npm test` — 20 testes DOM/lógica, incluindo contratos de criação, edição e exclusão, carrossel, permissões, teclado, filtros, carregamento progressivo e respostas atrasadas. Rede simulada somente nos testes; nenhuma navegação de browser ou escrita no banco real.
- `frontend`: `npm run lint` — sem erros; permanecem cinco avisos anteriores de imagens na fila facial. TypeScript e build de produção aprovados.
- `backend`: 60 testes existentes aprovados; nenhuma mudança de API, banco ou dados necessária nesta reformulação.
- **Pendente:** checklist visual e responsivo em navegador real. A automação de navegador foi bloqueada neste ambiente; testes DOM não confirmam pixels, rolagem e foco nativo.
- A lista renderiza progressivamente, mas usa o contrato atual que retorna todas as publicações autorizadas. Paginação no servidor permanece uma possível evolução, sem alterar este MVP.
- Auditoria de dependências (`npm audit`): 19 alertas (16 moderados, 2 altos e 1 crítico), incluindo o Next.js atualmente instalado. A revisão de versões/segurança ficou pendente e separada desta alteração visual; não foi aplicado `audit fix --force` nem alterado o framework automaticamente.

### Regularização da autoria na base local — 31/10/2026

- Por solicitação explícita, cinco publicações antigas da Escola Girassol, que exibiam “Professora Escola Girassol” e estavam sem autoria de conta, foram vinculadas à conta `professora@girassol.com`. Uma sexta publicação já tinha o vínculo correto.
- Antes da alteração, foram conferidos escola, conta ativa, turmas atribuídas e ausência de outra autoria. Após a transação, as seis publicações passaram na verificação de permissão de gestão da professora.
- Legendas, datas, fotos, turmas e destinatários foram preservados. As regras gerais de autorização não foram alteradas: não há atribuição automática de autoria pelo nome.
- Essa foi uma correção de dados no banco local, não uma migração distribuída pelo Git. Fazer pull desta branch não transfere esses vínculos para outro banco. Não executar seed para reproduzir a correção; outros ambientes exigem conferência e autorização próprias.
- [ ] Atualizar a página de Publicações com a conta da professora e conferir Editar/Excluir nas seis publicações regularizadas.
