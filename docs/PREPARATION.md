# Przygotowanie i późniejsza publikacja

Źródło: pełny odczyt aktywnego katalogu integracji przez SSH, nie kopia z 14 października. Pełny eksport zachowano prywatnie poza repozytorium. Sprawdzono SHA-256 każdego pliku podczas transferu i ponowny odczyt źródła w obrębie eksportu. Eksport obejmuje 41 plików integracji (w tym 13 cache) i 11 plików dystrybucji biblioteki.

Wersja źródłowa 2.1.5-beta.10; lokalne wydanie 2.1.5-mudiro.1. Zmiany przygotowawcze: wersja i przypięcie biblioteki 0.3.8 w manifeście, neutralizacja przykładowego MAC w dwóch plikach, dodanie translations/en.json z strings.json, dokumentacja i testy. Pozostałe źródła i grafiki są zgodne z eksportem. Kod sterowania pozostał identyczny bajt po bajcie. AST wszystkich modułów jest zgodny po uwzględnieniu jedynej zmiany tekstu przykładu adresu w formularzu config_flow.py.

Środowisko źródłowe: HA 2026.10.2, Python 3.14.6, bleak 3.0.2, bleak-retry-connector 4.7.1, voluptuous 0.16.0. Ostatnie trzy biblioteki są dostarczane przez środowisko HA/Bluetooth; nie dodajemy konkurencyjnych pinów. Biblioteka diesel-heater-ble 0.3.8 wymaga Python >=3.10, nie deklaruje dodatkowych zależności wykonawczych. Cztery pliki pakietu są identyczne z wheel PyPI; SHA-256 wheel: 2079f15b5a5f6a2ff59549786ad78a5b38f86d3357c01635f35255953d9b6a94. Nie trzeba pakować jej kopii do integracji.

## Wymagania HACS sprawdzone 19 października 2026

- Jedna integracja w custom_components/diesel_heater, wymagane pola manifestu, README i hacs.json w korzeniu, zasoby brand w integracji.
- Publiczne repozytorium GitHub; dla instalacji z domyślnej gałęzi release ani archiwum ZIP nie są wymagane.
- Nie używamy zip_release ani content_in_root. Domena pozostaje diesel_heater.
- documentation i issue_tracker wskazują https://github.com/RobGeePL/homeassistant-diesel-heater-mudiro oraz /issues; codeowners: @RobGeePL. Oryginalne autorstwo pozostaje w README i LICENSE.

Źródła: https://www.hacs.xyz/docs/publish/integration/ ; https://www.hacs.xyz/docs/publish/start/ ; https://www.hacs.xyz/docs/faq/custom_repositories/ ; https://contributors.home-assistant.io/core/integrations/manifest/ ; https://esphome.io/components/bluetooth_proxy/ .

## Kroki po uzyskaniu osobnej zgody na publikację

1. Konto i repozytorium ustalone: RobGeePL/homeassistant-diesel-heater-mudiro (publiczne). Przejrzeć raport i różnice.
2. Puste repozytorium zostało utworzone przez użytkownika. Sprawdzić opis i tematy home-assistant, hacs, diesel-heater, mudiro.
3. URL i opiekun uzupełnione lokalnie. Ponowić weryfikację, jeśli pliki ulegną zmianie.
4. Skonfigurować lokalnego autora Git świadomie: dane autora commitu będą publiczne. Dodać pliki i utworzyć commit lokalny, ustawić remote na ustalony adres i wykonać push dopiero za zgodą.
5. Ustawić main jako gałąź domyślną. Opcjonalnie utworzyć release z tagiem v2.1.5-mudiro.1, zgodnym z manifestem; nie wymaga ręcznego ZIP.
6. Przekazać koledze adres i instrukcję README; sprawdzić pobranie przez HACS na jego lub osobnym testowym HA. Takiego testu nie wykonano w działającej instalacji.

MIT zachowano w całości. Grafiki pochodzą z integracji bazowej i zachowano je w ramach jej licencji; nie ustalono niezależnej historii każdego pliku graficznego. Nie dołączono aplikacji producenta ani jej zasobów.
