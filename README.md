# Diesel Heater — Mudiro DZ06 Neo

Modyfikacja istniejącej integracji Diesel Heater, dostosowana i testowana przez użytkownika z Mudiro DZ06 Neo. Nie jest to nowy projekt napisany od podstaw ani oficjalna integracja producenta. Przygotowana do instalacji przez niestandardowe repozytorium HACS; bez zgłoszenia do oficjalnego katalogu.

Repozytorium tej wersji: [RobGeePL/homeassistant-diesel-heater-mudiro](https://github.com/RobGeePL/homeassistant-diesel-heater-mudiro). Opiekun tej modyfikacji: @RobGeePL.

## Pochodzenie i licencja

Baza: [Spettacolo83/homeassistant-diesel-heater](https://github.com/Spettacolo83/homeassistant-diesel-heater), wcześniejszy projekt: [MSDATDE/homeassistant-vevor-heater](https://github.com/MSDATDE/homeassistant-vevor-heater). Zachowano oznaczenie Copyright (c) 2025 Sebastian Majchrzak i pełną licencję MIT w LICENSE. Biblioteka BLE pochodzi od Spettacolo83. Nie przypisujemy sobie autorstwa całej integracji. Projekt bazowy zawierał już część obsługi Neo; ta wersja zachowuje późniejsze poprawki z działającej instalacji. Nie zawiera aplikacji Sunster Neo ani jej plików.

## Wymagania

- Home Assistant Core 2026.10.2 lub nowszy; źródłowe środowisko działało z Pythonem 3.14.6. Nowsze wersje nie zostały przetestowane. Nie ustalono najstarszej zgodnej wersji; próg HACS jest celowo zachowawczy.
- HACS i dostęp HA do PyPI przy instalacji biblioteki diesel-heater-ble==0.3.8.
- Integracja Bluetooth w HA oraz adapter z obsługą połączeń BLE albo proxy ESPHome z aktywnymi połączeniami GATT (bluetooth_proxy, active: true), dodane przez integrację ESPHome i mające wolny slot połączenia.
- Zasilona nagrzewnica w zasięgu. Odłącz aplikację telefonu, jeśli zajmuje połączenie BLE.

## Instalacja u kolegi — po opublikowaniu repozytorium

1. Otwórz HACS w Home Assistant.
2. W menu wybierz Niestandardowe repozytoria, wklej `https://github.com/RobGeePL/homeassistant-diesel-heater-mudiro` i wybierz typ **Integration**.
3. Zainstaluj **Diesel Heater — Mudiro DZ06 Neo**.
4. Uruchom ponownie Home Assistant Core.
5. Otwórz **Ustawienia → Urządzenia i usługi → Dodaj integrację**.
6. Wybierz **Diesel Heater**. Wybierz wykryte urządzenie lub wpisz własny adres Bluetooth w ścieżce ręcznej. Ustaw hasło połączenia Neo właściwe dla swojego kontrolera (fabryczna wartość aplikacji: 100000000); starszy PIN jest odrębnym polem.

Nie trzeba pobierać ZIP ani kopiować plików ręcznie. Publiczne repozytorium zostało utworzone; instalacja będzie możliwa po przesłaniu plików za osobną zgodą.

**Wspólna domena:** diesel_heater. Ta wersja zastępuje pliki innej integracji o tej domenie; nie instaluje się obok niej jako drugi komponent. Jeśli używasz już wersji upstream, wykonaj kopię zapasową i wybierz jedno źródło aktualizacji w HACS. Aktualizacja z upstream może nadpisać poprawki Mudiro. Nie usuwaj wpisów urządzeń tylko po to, aby zmienić źródło plików.

## Zachowane możliwości

Neo: FFF0/FFF1/FFF2, autoryzacja, status, POWER ON/OFF, poziomy 1–10 przez 0x51 i potwierdzenie nastawy odpowiedzią kontrolera. Zachowano obsługę None, Problem/Error, napięcia i temperatur, a także późną rejestrację sześciu czujników Neo bez duplikatów: Fire Temperature, Fan Speed Raw, Frequency Raw, Fuel Raw, Remaining Time Raw, Igniter Current Raw.

Pozostałe ścieżki kodu: AA55, AA55 encrypted, AA66, AA66 encrypted, ABBA, CBFF, Hcalory MVP1/MVP2, HeatGenie/Boygu i Webasto Cronus. Hcalory XMZ-D1 może korzystać z AA55; marka nie przesądza protokołu. Nie deklarujemy testów wszystkich urządzeń.

## Ograniczenia

Różnice firmware mogą zmienić ramki, limity i zachowanie kontrolera. Pola Raw nie mają potwierdzonych jednostek. Zużycie paliwa jest szacunkiem. Nie wszystkie opcje eksperymentalne, w tym burn-off i ustawienia ogólne, zostały przetestowane na każdym urządzeniu. Nazwy encji i sensor protokołu mogą nadal wskazywać Vevor/ABBA także przy Neo — zachowano istniejące działanie i identyfikatory.

Nie włączaj debugowania bez potrzeby: odziedziczona diagnostyka Hcalory MVP2 może zapisywać PIN oraz ramkę autoryzacji w logach. Nie udostępniaj surowych logów bez ich sprawdzenia.

## Weryfikacja

`python3 -B -m unittest discover -s tests -v`

Testy wykonują wybrane oryginalne metody z AST na atrapach; nie wymagają HA ani Bluetooth. Nie zastępują pełnego testu instalacji HACS ani testu sprzętowego. Szczegóły przygotowania: docs/PREPARATION.md.
