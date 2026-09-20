# Integração Tinhaphone → Prisma → TinhaKids

## Resultado entregue

Os três projetos passaram a formar um único fluxo:

1. a professora tira uma foto no Tinhaphone;
2. o aplicativo salva a foto no aparelho e tenta enviá-la à API Prisma;
3. a foto aparece na central da turma no portal Prisma;
4. um profissional da escola seleciona a foto, escreve uma legenda e marca os alunos;
5. o Prisma cria uma publicação ou portfólio, com uma foto ou um carrossel, vinculada aos perfis familiares desses alunos;
6. o TinhaKids autentica o responsável e exibe somente as publicações dos filhos vinculados à conta.

O backend Prisma é a fonte central dos dados. O Google Drive deixou de fazer parte do caminho obrigatório. O código antigo da integração com Drive foi preservado no repositório para não apagar uma funcionalidade anterior, mas a interface principal do Tinhaphone não depende mais dela.

## Decisões tomadas

### Vínculo seguro entre aluno e família

Foi criada a tabela `student_child_link`. Ela relaciona o aluno usado pelo portal escolar (`Student`) ao perfil de criança usado pelo aplicativo dos pais (`Child`). A publicação não tenta adivinhar a criança pelo nome.

Esse desenho impede que homônimos ou alterações de grafia enviem uma foto à família errada. O Prisma só permite selecionar para publicação os alunos que possuem perfil familiar vinculado.

### Foto e publicação são etapas diferentes

O envio do Tinhaphone cria uma `Photo`, que fica como material recebido pela escola. Somente a ação explícita no portal cria um `Post`. Assim, uma captura não aparece automaticamente para os pais sem revisão, legenda e seleção dos alunos.

### Falha de rede não perde a foto

O Tinhaphone salva primeiro no banco local e depois envia. Os estados são:

- `pending`: aguardando envio;
- `syncing`: envio em andamento;
- `synced`: recebida pelo Prisma, com o identificador remoto salvo;
- `error`: falhou e pode ser reenviada.

A tela inicial mostra esses estados, permite tentar novamente e mantém um histórico local dos erros.

## Prisma — backend

### Upload autenticado

O endpoint `POST /api/photos/upload` agora:

- exige token de um usuário escolar;
- usa o usuário do token como autor, sem aceitar um identificador arbitrário no formulário;
- exige a turma e verifica se a professora tem acesso a ela;
- aceita somente extensões de imagem suportadas;
- troca o nome original por um UUID, evitando colisões e nomes de arquivo inseguros;
- remove o arquivo se a gravação no banco falhar.

O acesso aos arquivos também normaliza o nome recebido para impedir navegação para fora da pasta de uploads.

### Criação de postagem

Foi criado `POST /api/posts/`. O endpoint recebe uma ou várias fotos:

```json
{
  "photo_ids": [10, 11, 12],
  "caption": "Hoje exploramos as cores.",
  "student_ids": [21, 22]
}
```

Antes de publicar, a API valida:

- acesso do usuário à turma;
- existência das fotos e se todas são da mesma turma;
- legenda não vazia;
- pelo menos um aluno selecionado;
- todos os alunos pertencem à turma da foto;
- todos possuem perfil familiar vinculado.

Também foi criado `GET /api/posts/?class_id=...` para o histórico escolar da turma.

O endpoint `POST /api/portfolio/` usa a mesma seleção múltipla e cria um projeto individual para cada criança escolhida, com título, descrição, objetivos pedagógicos e galeria de imagens.

### Correções de upload e exibição

O erro de envio do Tinhaphone tinha duas causas cobertas:

- imagens AVIF/HEIC produzidas ou compartilhadas por celulares agora são aceitas, além de JPEG, PNG e WebP;
- a rota segura usada pelo TinhaKids procurava os arquivos em `backend/app/uploads`, mas o upload real grava em `backend/uploads`. As duas rotas agora apontam para a mesma pasta.

Foi validado um upload AVIF real pela API (`HTTP 201`) e a leitura da mesma mídia pela rota assinada (`HTTP 200`, `image/avif`). O registro temporário usado nesse teste foi removido em seguida.

Após o teste visual no TinhaKids, foi adicionada uma camada de compatibilidade: arquivos AVIF, HEIC e HEIF continuam preservados no formato original, mas a rota de mídia gera uma representação JPEG para os aplicativos. Isso evita falhas de decodificação do Flutter sem reduzir ou substituir o arquivo original. A postagem local de teste foi validada novamente com resposta `HTTP 200` e `image/jpeg`.

### Vínculos familiares

Foram adicionados os endpoints `GET /api/families/children`, `PUT /api/families/students/{id}` e `POST /api/families/students/{id}`. Eles permitem listar perfis já cadastrados, reaproveitar um perfil familiar existente ou cadastrar um novo responsável e criar o vínculo em uma única operação.

No modal “Vincular”, a escola pode escolher um perfil existente. Se a família ainda não existir, informa nome, e-mail, telefone opcional e uma senha inicial de pelo menos seis caracteres. A conta fica ativa e o responsável pode entrar imediatamente no TinhaKids. Um e-mail já cadastrado é reaproveitado sem trocar a senha existente.

O cadastro existente de Pedro, que estava sem relação no banco atual, foi vinculado ao perfil `pedro`. A correção também ficou no seed para bancos recriados no futuro.

### Feed dos pais

O endpoint existente `GET /api/v1/posts/?child_id=...` continua protegido pelo token do responsável. A dependência `verifyChildAccess` confirma que a criança solicitada pertence à conta autenticada. As postagens agora são devolvidas da mais recente para a mais antiga.

As URLs das imagens locais continuam assinadas e expiram. O acesso de mídia recebeu validação adicional do caminho do arquivo.

### Dados de demonstração

A carga inicial cria:

- a professora Marília no Grupo 2;
- os alunos Pedro e Sofia no Grupo 2;
- os perfis familiares Pedro e Sofia;
- o vínculo explícito entre cada aluno e seu perfil familiar;
- a conta responsável `teste@teste.com` com acesso aos dois perfis.

## Prisma — portal web

Toda a aparência foi convertida para tema claro, com componentes discretos e padrão: fundo cinza-claro, cartões brancos, bordas neutras e azul como cor de ação.

A página da turma foi refeita como biblioteca e central de publicações:

- grade com as fotos recebidas do Tinhaphone;
- filtros por aluno, intervalo de datas e tag;
- organização cronológica por mês, que pode ser ligada ou desligada;
- seleção de uma ou várias fotos;
- criação de publicação em modal, incluindo carrossel;
- criação de portfólio a partir da mesma seleção múltipla;
- modal para vincular alunos a perfis familiares, exibindo nome e e-mail dos responsáveis;
- indicação clara para aluno sem perfil familiar;
- confirmação de que a publicação já está disponível aos pais;
- histórico das publicações recentes.

A lateral deixou de ser o formulário de publicação. Ela mostra somente as informações da foto ativa: data, autor do envio, alunos identificados, descrição e tags. As tags podem ser aplicadas ou removidas ali mesmo.

O painel de turmas e o login também foram padronizados em tema claro. A URL da API pode ser configurada por `NEXT_PUBLIC_API_URL`; o exemplo está em `prisma/frontend/.env.local.example`.

O arquivo de proteção de rotas foi atualizado de `middleware.ts` para `proxy.ts`, conforme a convenção da versão atual do Next.js usada pelo projeto.

## Tinhaphone

Foi criado `PrismaApiService`, responsável por:

- autenticar a professora;
- testar a conexão;
- consultar as turmas disponíveis;
- enviar a imagem em formulário multipart;
- devolver o identificador criado no Prisma.

A tela principal foi simplificada para o fluxo da câmera escolar. Ela mostra fotos locais, situação do envio, reenvio e acesso às configurações. A tela de configurações possui:

- endereço da API;
- e-mail da professora;
- senha;
- código da turma;
- teste de conexão com listagem das turmas acessíveis.

Valores locais padrão:

- API no emulador Android: `http://10.0.2.2:8000`;
- API em iOS/desktop: `http://127.0.0.1:8000`;
- professora: `marilia@school.com`;
- senha: `mypassword`;
- turma: `2` (Grupo 2 depois da carga inicial).

Na primeira abertura do Tinhaphone, a tela de configuração é aberta automaticamente. Salve os dados e use “Testar conexão e listar turmas” antes de fotografar; depois disso o aplicativo reutiliza essa configuração e envia as fotos sem pedir login a cada captura.

O banco SQLite local foi atualizado para a versão 3, adicionando `prismaPhotoId` e `uploadError`. A atualização preserva registros já existentes.

Android e iOS receberam a configuração necessária para acessar a API HTTP local durante o desenvolvimento. Em produção, a API deve usar HTTPS e essas permissões devem ser restringidas.

## TinhaKids

O aplicativo deixou de usar `MockData` para autenticação, crianças, feed e portfólio. Foi criado `TinhaKidsApiService` e um estado central Riverpod que mantém:

- token da família;
- crianças vinculadas;
- criança selecionada;
- publicações reais;
- projetos reais;
- carregamento e erro.

O login agora valida as credenciais no backend. Ao entrar, o aplicativo carrega as crianças da conta e busca o feed da criança selecionada. A troca entre Pedro e Sofia faz uma nova consulta autorizada.

A interface foi aproximada do Material padrão: AppBar simples, NavigationBar, cartões com borda, controles de seleção e estados de vazio/erro/carregamento. O feed mostra professora, turma, data, imagem e legenda. Publicações com mais de uma foto agora têm navegação por carrossel e contador de posição.

Foi criada a terceira página **Perfil**. Ela mostra avatar, nome, turma e totais da criança, permite trocar de filho, reúne todas as fotos publicadas num grid quadrado e oferece tanto a separação por ano quanto o filtro para um ano específico. Ao tocar numa foto, o responsável vê a imagem ampliada, a legenda e a data. Projetos de portfólio com várias fotos também possuem carrossel na página de detalhes.

O controle de separação por ano foi reduzido para um chip compacto “Por ano”, acompanhado de um pequeno seletor de ano. Ele não ocupa mais uma linha destacada inteira do perfil.

### Sessão persistente no TinhaKids

O token já era salvo localmente, mas não era restaurado durante a inicialização. Agora o aplicativo verifica a sessão antes de abrir o login, recupera as crianças, restaura a última criança selecionada e carrega o feed automaticamente. O botão “Sair” continua removendo todos esses dados.

Os tokens familiares passaram a ter validade de 30 dias. Se o token estiver ausente, expirado ou inválido, o aplicativo limpa a sessão e mostra o login normalmente.

Endereços padrão:

- navegador: `http://localhost:8000`;
- emulador Android: `http://10.0.2.2:8000`;
- iOS/desktop: `http://127.0.0.1:8000`.

Para outro endereço, compile ou execute com `--dart-define=API_URL=http://ENDERECO:8000`.

## Segurança e privacidade

Foram aplicadas as seguintes proteções relevantes:

- upload associado ao usuário autenticado;
- autorização por turma para professores;
- validação de tipo e extensão de imagem, incluindo AVIF e HEIC;
- nomes aleatórios para arquivos recebidos;
- bloqueio de caminhos de arquivo manipulados;
- postagem somente para alunos da mesma turma;
- vínculo explícito aluno–perfil familiar;
- consulta de feed somente pelo responsável vinculado;
- galerias N:N para reutilizar fotos em publicações e portfólios.

As credenciais incluídas são apenas dados locais de demonstração. Antes de produção é necessário trocar o `SECRET_KEY`, usar HTTPS, guardar segredos fora do repositório, definir política de expiração/renovação de sessão e substituir o armazenamento local de arquivos por um serviço com controle de acesso e backup.

## Arquivos principais alterados

### Backend

- `prisma/backend/app/models.py`
- `prisma/backend/app/schemas.py`
- `prisma/backend/app/photos.py`
- `prisma/backend/app/publishing.py`
- `prisma/backend/app/school_portfolio.py`
- `prisma/backend/app/families.py`
- `prisma/backend/app/students.py`
- `prisma/backend/app/routers/posts.py`
- `prisma/backend/app/routers/media.py`
- `prisma/backend/app/routers/auth_parents.py`
- `prisma/backend/app/main.py`
- `prisma/backend/app/seed.py`
- `prisma/backend/tests/test_publication_flow.py`

### Portal Prisma

- `prisma/frontend/app/page.tsx`
- `prisma/frontend/app/login/page.tsx`
- `prisma/frontend/app/class/[id]/page.tsx`
- `prisma/frontend/app/globals.css`
- `prisma/frontend/app/layout.tsx`
- `prisma/frontend/context/AuthContext.tsx`
- `prisma/frontend/proxy.ts`

### Tinhaphone

- `tinhaphone/lib/services/prisma_api_service.dart`
- `tinhaphone/lib/services/db_service.dart`
- `tinhaphone/lib/models/photo.dart`
- `tinhaphone/lib/screens/home_screen.dart`
- `tinhaphone/lib/screens/settings_screen.dart`
- configurações Android/iOS e teste de persistência

### TinhaKids

- `tinhakids/lib/services/tinhakids_api_service.dart`
- `tinhakids/lib/providers/app_state.dart`
- modelos JSON de criança, publicação e projeto
- telas de login, feed, portfólio, perfil e navegação
- tema Material claro, configurações Android/iOS e teste de interface

## Verificações executadas

- `npm run build` no portal Prisma: aprovado;
- `npm run lint` no portal Prisma: aprovado;
- `flutter build web` no TinhaKids: aprovado;
- `flutter build apk --debug` no Tinhaphone: aprovado;
- `flutter build apk --debug` no TinhaKids: aprovado;
- `flutter test` no TinhaKids: aprovado;
- `flutter test` no Tinhaphone: aprovado;
- compilação de todos os módulos Python: aprovada;
- três testes automatizados de publicação, carrossel, portfólio, isolamento e cadastro familiar: aprovados;
- teste real de upload AVIF e leitura da mídia assinada: aprovado;
- login familiar e consulta da postagem de Sofia com a imagem real: aprovados;
- vínculo Pedro → perfil familiar no banco atual: confirmado.

O Tinhaphone não possui alvo web no projeto e depende de câmera, por isso sua validação final de interface deve ser feita em Android ou iOS. O APK de debug foi gerado com sucesso usando o atalho que configura o diretório temporário curto exigido pelo Gradle no Windows.
