# Dépôt _Foxync_

## Auteur
Mathias Amato

## Description
Foxync est un outil de synchronisation de fichiers open source proposant à ses utilisateurs un moyen simple de garder des copies de fichiers sur plusieurs appareils en local, grâce au protocole Bittorrent. Un serveur central sauvegarde quelques informations importantes comme le pseudo et mot de passe de l'utilisateur, et des informations des différents appareils. Il orchestre aussi la synchronisation entre chaque appareil, en informant les modifications apportées dans tout le réseau et en mettant en relation les clients. La gestion des fichiers se fait depuis l'explorateur de fichiers dans un dossier dedié à Foxync, et une application installable permet de configurer des paramètres et avoir une vue d'ensemble des appareils et de la synchronisation.

<img style="width: 64px; height: 100%;" src="./docs/medias/logo-foxync_no_background.png"/>

### [Lien vers la documentation](https://mathias-amt.docs.ictge.ch/foxync/)

## Mise en place

Cette marche à suivre utilise zypper. Le gestionnaire de paquets et les noms des paquets peuvent changer selon la distribution.

### Cloner le dépôt en local
```sh
git clone https://gitlab.ictge.ch/mathias-amt/foxync.git
```

### Installer la librairie de headers et fichiers de configuration Python
```sh
sudo zypper install python3-devel
```

### Installer la librairie libtorrent (Le nom des paquets et du package manager changent selon la distribution)
```sh
sudo zypper install libtorrent21 python3-libtorrent-rasterbar
```

### Installer les librairies de développement mariadb, qui permettent ensuite d'installer le paquet Pypi (Le nom des paquets et du package manager changent selon la distribution)
```sh
sudo zypper install libmariadb3 libmariadb-devel
```

### Créer et activer l'environnement virtuel
```sh
cd foxync
python3 -m venv ./venv/ --system-site-packages
source ./venv/bin/activate
```

### Installer les bibliothèques nécessaires
```sh
pip install -r requirements-app.txt
```
