Fluxo do Sistema de planilhas - Logae

1. Acesso ao Sistema
  - O usuário acessa a aplicação
  - A primeira tela exibida é a de login.

2. Login do Usuário (auth.py) 
  - O usuário informa nome de usuário e senha.
  - O sistema verifica os dados no arquivo dados_usuarios.json.
  - Se válido, define o nível de acesso (admin ou padrão ) e salva na sessão.
  - A ação de login é registrada no histórico do usuário.

3. Interface e Navegação (app.py)
    Após login:
  - Usuário padrão vê apenas o "Editor de Planilhas".
  - Admin vê "Editor de Planilhas", "Dashboard" e "Gerenciar Usuários".

4. Upload e Processamento de Planilhas (processor.py)
  - O usuário digita o código da empresa e envia arquivos CSV ou Excel.
  - O sistema detecta automaticamente as colunas de placa, data e hora, latitude e longitude.
  - Os dados são formatados (placa, data, coordenadas, código da empresa).
  - Os arquivos editados podem ser baixados individualmente ou em um arquivo ZIP.
  - As ações de edição e download são registradas no JSON.

5. Dashboard (analytics.py)
  -Visível apenas para administradores.
    Exibe:
  - Gráfico de edições por mês.
  - Gráfico de edições por usuário.
Além de um botão pra limpar o histórico de edições

6. Gerenciamento de Usuários (admin.py)
    Admin pode:
  - Criar, editar e remover usuários.
  - Visualizar histórico de ações de cada usuário.

7. Armazenamento de Dados (data_handler.py + dados_usuarios.json)
    Todos os dados abaixo são salvos no arquivo dados_usuarios.json:
  - Usuários, níveis e histórico.
  - Planilhas editadas.
  - Downloads realizados.
  - O data_handler.py garante que o JSON esteja sempre inteiro e funcionando.

8. Logout:
  - O botão "Sair" limpa a sessão e retorna à tela de login.
