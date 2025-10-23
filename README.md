# kataduke
app sakusei

## 機能
- アプリ説明ページ → ログイン画面 → メイン画面 
- メイン画面からメニューを開いて各機能に移動
- アルバム、カメラ、todo
- ログアウト機能

## 開発環境
- Python 3.10+
- Flask
- HTML/CSS/JavaScript

## セットアップ方法
資格情報マネージャーを検索してgithubの情報を消しておく<br>

1. VSCodeに自分の情報を登録する<br>
  ・vscode内のターミナル<br>
  git config –global user.name githubのID<br>
  git config –global user.email メアド<br>
  （登録情報を確認するときは git config –global user.name(またはuser.email）

3. リポジトリをクローンする<br>
  git clone https://github.com/kvv7ma/kataduke.git<br>
  cd kataduke

普通に噓の可能性がある↓
~~### 作業内容を保存するとき~~
  ~~VSCode内ターミナル<br>~~
    ~~git add .<br>~~
    ~~git commit -m "(作業内容にタイトルをつける)"（例："first commit"、"album sakusei"など）<br>~~
    ~~git push origin main <br>~~
