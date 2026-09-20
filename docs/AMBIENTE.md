# Ambiente de desenvolvimento

Esta pasta reúne três projetos independentes que agora compartilham o mesmo fluxo de fotos:

| Projeto | Tecnologia | Função |
| --- | --- | --- |
| `prisma` | FastAPI + Next.js + PostgreSQL | API central e portal de publicação |
| `tinhaphone` | Flutter | Captura e envio das fotos escolares |
| `tinhakids` | Flutter | Feed e portfólio das famílias |

## Primeira inicialização

Depois de atualizar o Docker Desktop e reiniciar o Windows, abra um PowerShell nesta pasta e execute:

```powershell
.\iniciar-prisma.ps1 -Seed
```

O `-Seed` recria o banco e prepara os vínculos de demonstração. Use-o somente na primeira carga ou quando quiser apagar e recriar os dados locais. Depois disso, inicie normalmente com:

```powershell
.\iniciar-prisma.ps1
```

O portal fica em `http://localhost:3000`, a API em `http://localhost:8000` e a documentação interativa em `http://localhost:8000/docs`.

## Aplicativos

TinhaKids no navegador:

```powershell
.\iniciar-tinhakids.ps1
```

Tinhaphone no emulador Android:

```powershell
.\iniciar-tinhaphone.ps1
```

Na primeira abertura do Tinhaphone, salve a configuração do Prisma e teste a conexão. Nas próximas aberturas, ela fica guardada no aparelho.

O Tinhaphone usa `http://10.0.2.2:8000` no emulador. Em um celular físico, abra Configurações no aplicativo e troque o endereço pelo IP deste computador na rede, por exemplo `http://192.168.1.20:8000`.

Os atalhos Flutter definem `C:\tmp` como diretório temporário do processo para contornar um limite de caminho do canal local do Gradle no Windows. Não é necessário configurar isso manualmente ao usar os scripts.

## Contas locais

- Professora no Prisma e Tinhaphone: `marilia@school.com` / `mypassword`
- Família no TinhaKids: `teste@teste.com` / `123456`
- Administração do Prisma: `admin@school.com` / `mypassword`

Pedro e Sofia estão vinculados à conta familiar de teste e ao Grupo 2. O código padrão dessa turma no banco recém-criado é `2`.

## Situação específica desta máquina

O Docker Desktop 4.44.3 instalado está com um serviço interno antigo travado e o Windows possui uma operação de arquivo pendente. Para executar PostgreSQL e builds Android sem a falha de conexão local:

1. atualize o Docker Desktop em um PowerShell aberto como administrador;
2. reinicie o Windows;
3. abra o Docker Desktop e espere o estado `Running`;
4. rode a primeira inicialização acima.

As dependências de Node, Python e Flutter já foram instaladas. O frontend Prisma gera a versão de produção, o TinhaKids gera a versão web, o APK de debug do Tinhaphone gera normalmente e os testes automatizados dos três projetos estão passando.

Consulte `IMPLEMENTACAO_INTEGRACAO.md` para a descrição completa das decisões e mudanças.
