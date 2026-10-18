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

## Decizii de implementare

1. **Stocare in memorie**: Datele sunt tinute in memorie (clasa `Store`), conform cerintei temei. La restart, datele se pierd.
2. **Validare stricta**: Campurile obligatorii sunt verificate, iar erorile sunt returnate cu coduri HTTP corecte (409 pentru conflict, 404 pentru resursa lipsa).
3. **Calcul zile restante**: `days_overdue` se calculeaza față de data curenta (sau parametrul `as_of`), returnand 0 daca imprumutul nu este restant.
