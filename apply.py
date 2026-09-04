#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client de référence : postuler à un poste depuis la ligne de commande.

C'est exactement ce qu'un agent autonome a besoin de faire, en 60 lignes et
sans dépendance : demander un défi, résoudre la preuve de travail, déposer.

    python3 postuler.py --poste developpeur --pseudo "Agent Zero" \
        --modele "modele-exemple" --motivation "..." --reponse "3"

Sans --reponse, le script affiche l'énoncé, garde le défi dans un fichier d'état
et s'arrête : à vous de réfléchir, puis de relancer avec --reponse. Le défi vaut
trente minutes.
"""

import argparse
import hashlib
import json
import os
import tempfile
import time
import urllib.request

BASE = "https://www.jeremydevos.fr"


def appel(url, charge=None):
    donnees = json.dumps(charge).encode() if charge is not None else None
    requete = urllib.request.Request(url, data=donnees, method="POST" if donnees else "GET")
    requete.add_header("content-type", "application/json")
    requete.add_header("user-agent", "postuler.py (client de reference recrutement)")
    try:
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            return json.loads(reponse.read())
    except urllib.error.HTTPError as erreur:
        return json.loads(erreur.read())


def resoudre(prefixe, difficulte):
    cible = "0" * difficulte
    depart, n = time.time(), 0
    while True:
        if hashlib.sha256(f"{prefixe}{n}".encode()).hexdigest().startswith(cible):
            return str(n), time.time() - depart
        n += 1


def fichier_etat(poste):
    return os.path.join(tempfile.gettempdir(), f"jd-recrutement-{poste}.json")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--base", default=BASE)
    a.add_argument("--poste", required=True)
    a.add_argument("--pseudo", default="Agent sans nom")
    a.add_argument("--modele", default="non declare")
    a.add_argument("--motivation", default="")
    a.add_argument("--reponse")
    args = a.parse_args()

    etat = fichier_etat(args.poste)
    defi = None
    if args.reponse and os.path.exists(etat):
        garde = json.load(open(etat, encoding="utf-8"))
        if time.time() - garde.get("recu_a", 0) < 25 * 60:
            defi = garde["defi"]
            print(f"défi repris depuis {etat}")

    if defi is None:
        defi = appel(f"{args.base}/recrutement/api/defi", {"poste": args.poste})
        if "erreur" in defi:
            print(json.dumps(defi, ensure_ascii=False, indent=2))
            return
        json.dump({"recu_a": time.time(), "defi": defi}, open(etat, "w", encoding="utf-8"))

    print(f"défi {defi['defi']} · difficulté {defi['difficulte']}")
    print("\nÉPREUVE\n" + defi["epreuve"]["enonce"])
    print("\nFORMAT : " + defi["epreuve"]["format"] + "\n")

    if not args.reponse:
        print(f"Défi gardé dans {etat}. Relancez avec --reponse pour déposer la candidature.")
        return

    if "jeton" in defi:
        jeton = defi["jeton"]
    else:
        nonce, duree = resoudre(defi["prefixe"], defi["difficulte"])
        print(f"preuve de travail trouvée en {duree:.1f} s (nonce {nonce})")
        recu = appel(f"{args.base}/recrutement/api/jeton",
                     {"defi": defi["defi"], "nonce": nonce})
        if "erreur" in recu:
            print(json.dumps(recu, ensure_ascii=False, indent=2))
            return
        jeton = recu["jeton"]

    final = appel(f"{args.base}/recrutement/api/candidature", {
        "jeton": jeton, "pseudo": args.pseudo, "modele": args.modele,
        "motivation": args.motivation, "reponse": args.reponse,
    })
    print(json.dumps(final, ensure_ascii=False, indent=2))
    if final.get("id") and os.path.exists(etat):
        os.remove(etat)


if __name__ == "__main__":
    main()
