# Registru de împrumuturi

![CI](https://github.com/ovictorot/map_proiect_/actions/workflows/ci.yml/badge.svg)

Proiect individual la disciplina Metode avansate de programare, anul universitar 2026-2027.

## Autor

- **Nume:** Otean Victor
- **Grupa:** 2.1
- **Marca:** LH715740
- **Tema:** 6 - Registru de împrumuturi

## Descriere

Serviciu web RESTful pentru evidența cărților și a împrumuturilor dintr-o bibliotecă, dezvoltat conform cerințelor temei 6.

## Tehnologii

Python 3.13 cu Flask

## Rulare

```
docker build -t map-proiect .
docker run -d -p 8080:8080 map-proiect
```

Aplicatia asculta pe portul 8080. Verificati:

```
curl http://localhost:8080/health
curl http://localhost:8080/version
```

## Testare

```
pip install -r requirements.txt pytest pytest-cov
python -m pytest --cov=src
```

## Rutele implementate

| Ruta | Metoda | Descriere |
|---|---|---|
| `/health` | GET | Starea serviciului |
| `/version` | GET | Versiunea si commit-ul din care a fost construita imaginea |
| `/` | GET | Pagina de prezentare |
| `/reset` | POST | Goleste datele din memorie |
| `/books` | POST | Adauga o carte noua |
| `/books` | GET | Lista carților cu exemplare disponibile |
| `/loans` | POST | Inregistreaza un imprumut nou |
| `/loans/{id}/return` | POST | Returneaza un imprumut |
| `/loans` | GET | Lista imprumuturilor (filtrare: active, restante) |
| `/admin/stats` | GET | Extensie: Statistici globale protejate prin HTTP Basic Auth (`ADMIN_USER`, `ADMIN_PASSWORD`) |

## Extensii implementate

- **Extensia 1 - Persistență în Cloudflare R2 / depozit compatibil S3**:
  - Salvarea automată a stării aplicației la fiecare modificare (`POST /books`, `POST /loans`, `POST /loans/{id}/return`, `POST /reset`).
  - Reîncărcarea automată a datelor la pornirea containerului (`Store.load_from_s3()`), prevenind pierderea stării la restart.
  - Configurare dinamică exclusiv prin variabilele de mediu standardizate: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` (fără credențiale hardcodate în cod sau comise în Git).
  - Folosește biblioteca universală `boto3` compatibilă cu orice serviciu S3 standard.

- **Extensia 2 - Rută administrativă protejată (`/admin/stats`)**:
  - Autentificare securizată prin standardul HTTP Basic.
  - Credențialele sunt preluate dinamic din variabilele de mediu `ADMIN_USER` și `ADMIN_PASSWORD` (fără valori stocate în cod).
  - Returnează codul `401 Unauthorized` cu antet `WWW-Authenticate` și mesaj standardizat JSON în cazul lipsei sau invalidității credențialelor.
  - Returnează statistici agregate în format JSON: număr total de cărți, total exemplare, exemplare disponibile, total împrumuturi, împrumuturi active, împrumuturi returnate și împrumuturi returnate cu întârziere.

## Decizii de implementare

1. **Stocare in memorie**: Datele sunt tinute in memorie (clasa `Store`), conform cerintei temei. La restart, datele se pierd.
2. **Validare stricta**: Campurile obligatorii sunt verificate, iar erorile sunt returnate cu coduri HTTP corecte (409 pentru conflict, 404 pentru resursa lipsa).
3. **Calcul zile restante**: `days_overdue` se calculeaza față de data curenta (sau parametrul `as_of`), returnand 0 daca imprumutul nu este restant.
