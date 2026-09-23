"""
Tłumaczenia treści modułów DEMO (4 segmenty) na en / uk / es / ru.
Zapisuje do onboarding_module_translations (upsert po tytule polskim modułu).
Tłumaczenia zrobione w sesji (Claude, 23.09.2026), bez API. Znaczniki [plik N] zachowane.

Uruchomienie: set -a; source .env; set +a; .venv/bin/python seed_onboarding_translations.py
Na produkcji: DATABASE_URL=<public url> .venv/bin/python seed_onboarding_translations.py
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Tenant
import app.api.onboarding  # noqa
from app.models_onboarding import OnboardingSegment, OnboardingModule, OnboardingModuleTranslation

# klucz: (segment PL, tytuł PL) -> {lang: (tytuł, treść)}
T = {}

# ---------------------------------------------------------------- Automotive 1
T[("Automotive 1", "Bezpieczeństwo na hali")] = {
"en": ("Safety on the shop floor",
"The shop floor has rules that protect you and the people next to you. Read them carefully. Confirm at the end that you understand.\n\n"
"Moving around the floor\n\n"
"- Walk only along the marked pedestrian routes, the yellow lines on the floor.\n"
"- Forklifts have right of way. Stop and make eye contact with the operator before you cross.\n"
"- Do not enter areas marked with red tape or step behind machine guards.\n"
"- No running, no phone while walking.\n\n"
"[plik 1]\n\n"
"Emergency stops\n\n"
"Red STOP buttons are on every machine and on posts every 20 metres. Press one when you see danger to yourself or anyone else. "
"Do not wonder whether it is really necessary. A false alarm is never punished, no reaction can cost someone's health.\n\n"
"After an emergency stop, only the foreman or maintenance restarts the machine. Never try yourself.\n\n"
"[plik 2]\n\n"
"Noise and lighting\n\n"
"- In areas marked with the headphones pictogram wear hearing protection. You get it from the coordinator.\n"
"- Report a burnt-out or flickering light above your workstation.\n\n"
"Substances and materials\n\n"
"- Chemical containers are labelled. Do not pour them into other packaging.\n"
"- Spill: secure the area, do not clean it yourself, call the foreman.\n"
"- Used gloves and wipes go into the marked bins.\n\n"
"Accident or dangerous situation\n\n"
"- First make the area safe, then call for help.\n"
"- Emergency number: 112. First aid kits are at the floor entrances and by the foreman's office.\n"
"- Report every incident, even a small cut, to the Find Work coordinator the same day.\n\n"
"You will get the coordinator's number on your first day. Save it in your phone."),
"uk": ("Безпека в цеху",
"У цеху діють правила, які захищають вас і людей поруч. Прочитайте їх уважно. Наприкінці підтвердьте, що розумієте.\n\n"
"Пересування по цеху\n\n"
"- Ходіть лише позначеними пішохідними доріжками, жовтими лініями на підлозі.\n"
"- Навантажувачі мають перевагу. Зупиніться і встановіть зоровий контакт з оператором, перш ніж перейти.\n"
"- Не заходьте в зони, позначені червоною стрічкою, і за огорожі машин.\n"
"- Не бігайте, не користуйтеся телефоном на ходу.\n\n"
"[plik 1]\n\n"
"Аварійні вимикачі\n\n"
"Червоні кнопки STOP є на кожній машині та на стовпах кожні 20 метрів. Натисніть, коли бачите загрозу для себе або когось іншого. "
"Не роздумуйте, чи це справді потрібно. За хибну тривогу не карають, а відсутність реакції може коштувати здоров'я.\n\n"
"Після натискання вимикача машину запускає лише бригадир або служба обслуговування. Не пробуйте самі.\n\n"
"[plik 2]\n\n"
"Шум і освітлення\n\n"
"- У зонах з піктограмою навушників носіть захист слуху. Його видає координатор.\n"
"- Повідомте про перегорілу або миготливу лампу над вашим робочим місцем.\n\n"
"Речовини та матеріали\n\n"
"- Ємності з хімією мають етикетки. Не переливайте в інші упаковки.\n"
"- Розлив: огородіть місце, не прибирайте самі, покличте бригадира.\n"
"- Використані рукавиці та ганчір'я викидайте в позначені контейнери.\n\n"
"Нещасний випадок або небезпечна ситуація\n\n"
"- Спочатку подбайте про безпеку, потім кличте на допомогу.\n"
"- Телефон екстреної служби: 112. Аптечки є біля входів у цех і біля кабінету бригадира.\n"
"- Про кожну подію, навіть дрібний поріз, повідомте координатора Find Work того ж дня.\n\n"
"Номер координатора ви отримаєте першого дня. Збережіть його в телефоні."),
"es": ("Seguridad en la nave",
"En la nave rigen normas que te protegen a ti y a las personas de al lado. Léelas con atención. Al final confirma que las entiendes.\n\n"
"Cómo moverse por la nave\n\n"
"- Camina solo por las vías peatonales señalizadas, las líneas amarillas del suelo.\n"
"- Las carretillas elevadoras tienen preferencia. Detente y busca el contacto visual con el operador antes de cruzar.\n"
"- No entres en zonas marcadas con cinta roja ni detrás de las protecciones de las máquinas.\n"
"- No corras ni uses el teléfono mientras caminas.\n\n"
"[plik 1]\n\n"
"Paradas de emergencia\n\n"
"Los pulsadores rojos STOP están en cada máquina y en los pilares cada 20 metros. Púlsalos cuando veas un peligro para ti o para otra persona. "
"No te preguntes si es realmente necesario. Una falsa alarma no se sanciona, no reaccionar puede costar la salud.\n\n"
"Tras pulsar la parada, solo el encargado o mantenimiento vuelve a arrancar la máquina. No lo intentes tú.\n\n"
"[plik 2]\n\n"
"Ruido e iluminación\n\n"
"- En las zonas con el pictograma de auriculares usa protección auditiva. Te la entrega el coordinador.\n"
"- Avisa si una lámpara sobre tu puesto está fundida o parpadea.\n\n"
"Sustancias y materiales\n\n"
"- Los envases de productos químicos llevan etiqueta. No los traslades a otros envases.\n"
"- Derrame: asegura la zona, no limpies tú, llama al encargado.\n"
"- Los guantes y trapos usados van a los contenedores señalizados.\n\n"
"Accidente o situación peligrosa\n\n"
"- Primero pon a salvo la zona, después pide ayuda.\n"
"- Teléfono de emergencias: 112. Los botiquines están en las entradas de la nave y junto a la oficina del encargado.\n"
"- Comunica cualquier incidente, incluso un corte pequeño, al coordinador de Find Work el mismo día.\n\n"
"El número del coordinador lo recibirás el primer día. Guárdalo en tu teléfono."),
"ru": ("Безопасность в цеху",
"В цеху действуют правила, которые защищают вас и людей рядом. Прочитайте их внимательно. В конце подтвердите, что понимаете.\n\n"
"Передвижение по цеху\n\n"
"- Ходите только по обозначенным пешеходным дорожкам, жёлтым линиям на полу.\n"
"- Погрузчики имеют приоритет. Остановитесь и установите зрительный контакт с оператором, прежде чем перейти.\n"
"- Не заходите в зоны, обозначенные красной лентой, и за ограждения машин.\n"
"- Не бегайте, не пользуйтесь телефоном на ходу.\n\n"
"[plik 1]\n\n"
"Аварийные выключатели\n\n"
"Красные кнопки STOP есть на каждой машине и на столбах через каждые 20 метров. Нажмите, когда видите угрозу для себя или кого-то другого. "
"Не раздумывайте, действительно ли это нужно. За ложную тревогу не наказывают, а отсутствие реакции может стоить здоровья.\n\n"
"После нажатия выключателя машину запускает только бригадир или служба обслуживания. Не пробуйте сами.\n\n"
"[plik 2]\n\n"
"Шум и освещение\n\n"
"- В зонах с пиктограммой наушников носите защиту слуха. Её выдаёт координатор.\n"
"- Сообщите о перегоревшей или мигающей лампе над вашим рабочим местом.\n\n"
"Вещества и материалы\n\n"
"- Ёмкости с химией имеют этикетки. Не переливайте в другую тару.\n"
"- Разлив: оградите место, не убирайте сами, позовите бригадира.\n"
"- Использованные перчатки и ветошь выбрасывайте в обозначенные контейнеры.\n\n"
"Несчастный случай или опасная ситуация\n\n"
"- Сначала позаботьтесь о безопасности, потом зовите на помощь.\n"
"- Телефон экстренной службы: 112. Аптечки находятся у входов в цех и у кабинета бригадира.\n"
"- О каждом происшествии, даже мелком порезе, сообщите координатору Find Work в тот же день.\n\n"
"Номер координатора вы получите в первый день. Сохраните его в телефоне."),
}

T[("Automotive 1", "Odzież i obuwie ochronne")] = {
"en": ("Protective clothing and footwear",
"S3 safety shoes with toe caps are mandatory on the whole floor. The coordinator hands them out on your first day.\n\n"
"- High-visibility vest: always, also on the way to the changing room.\n"
"- Safety glasses: at workstations marked with the pictogram.\n"
"- Gloves: matched to your workstation, do not take gloves from another station.\n"
"- Long hair tied back, no jewellery on your hands."),
"uk": ("Захисний одяг і взуття",
"У всьому цеху обов'язкове захисне взуття S3 з металевим носком. Його видає координатор першого дня.\n\n"
"- Світловідбивний жилет: завжди, також дорогою до роздягальні.\n"
"- Захисні окуляри: на робочих місцях, позначених піктограмою.\n"
"- Рукавиці: підібрані до робочого місця, не беріть рукавиці з іншого місця.\n"
"- Довге волосся зібране, без прикрас на руках."),
"es": ("Ropa y calzado de protección",
"En toda la nave es obligatorio el calzado de seguridad S3 con puntera. Lo entrega el coordinador el primer día.\n\n"
"- Chaleco reflectante: siempre, también de camino al vestuario.\n"
"- Gafas de protección: en los puestos marcados con el pictograma.\n"
"- Guantes: adecuados a tu puesto, no cojas guantes de otro puesto.\n"
"- Pelo largo recogido, sin joyas en las manos."),
"ru": ("Защитная одежда и обувь",
"Во всём цеху обязательна защитная обувь S3 с металлическим носком. Её выдаёт координатор в первый день.\n\n"
"- Светоотражающий жилет: всегда, также по дороге в раздевалку.\n"
"- Защитные очки: на рабочих местах, обозначенных пиктограммой.\n"
"- Перчатки: подобранные под рабочее место, не берите перчатки с другого места.\n"
"- Длинные волосы собраны, без украшений на руках."),
}

T[("Automotive 1", "Stanowisko: opis maszyny")] = {
"en": ("Your workstation: the machine",
"You work on the wiring harness assembly line. The machine has three zones: feeding, crimping, inspection.\n\n"
"- Before starting, check that the guards are closed. The machine will not start with an open guard.\n"
"- Never reach into the crimping zone while the machine is running.\n"
"- Jam: stop the machine with the STOP button, then call the foreman. Do not clear jams yourself.\n"
"- End of shift: switch off, tidy the workstation, sign the card."),
"uk": ("Робоче місце: опис машини",
"Ви працюєте на лінії монтажу джгутів проводів. Машина має три зони: подача, обтиск, контроль.\n\n"
"- Перед запуском перевірте, чи закриті огорожі. Машина не запуститься з відкритою огорожею.\n"
"- Ніколи не тягніться в зону обтиску під час роботи машини.\n"
"- Заклинювання: зупиніть машину кнопкою STOP, потім покличте бригадира. Не усувайте заклинювання самі.\n"
"- Наприкінці зміни: вимкніть, приберіть робоче місце, впишіться в картку."),
"es": ("Tu puesto: la máquina",
"Trabajas en la línea de montaje de mazos de cables. La máquina tiene tres zonas: alimentación, crimpado, control.\n\n"
"- Antes de arrancar, comprueba que las protecciones están cerradas. La máquina no arranca con una protección abierta.\n"
"- Nunca metas la mano en la zona de crimpado con la máquina en marcha.\n"
"- Atasco: para la máquina con el botón STOP y avisa al encargado. No elimines atascos tú mismo.\n"
"- Al final del turno: apaga, ordena el puesto y firma la tarjeta."),
"ru": ("Рабочее место: описание машины",
"Вы работаете на линии сборки жгутов проводов. У машины три зоны: подача, обжим, контроль.\n\n"
"- Перед запуском проверьте, закрыты ли ограждения. Машина не запустится с открытым ограждением.\n"
"- Никогда не тянитесь в зону обжима во время работы машины.\n"
"- Заклинивание: остановите машину кнопкой STOP, затем позовите бригадира. Не устраняйте заклинивание сами.\n"
"- В конце смены: выключите, приберите рабочее место, распишитесь в карточке."),
}

T[("Automotive 1", "Pierwszy dzień i kontakt")] = {
"en": ("First day and contact",
"On your first day report to the Find Work coordinator at the main entrance. Bring your ID document.\n\n"
"- Changing room and locker: you get the key from the coordinator.\n"
"- Breaks: 15 minutes every 2 hours, 30 minutes for a meal.\n"
"- Report an absence to the coordinator at least 2 hours before the shift.\n\n"
"Questions? Write on WhatsApp, to the number you got this link from."),
"uk": ("Перший день і контакт",
"Першого дня зверніться до координатора Find Work біля головного входу. Візьміть із собою документ, що посвідчує особу.\n\n"
"- Роздягальня і шафка: ключ отримаєте від координатора.\n"
"- Перерви: 15 хвилин кожні 2 години, 30 хвилин на їжу.\n"
"- Про відсутність повідомляйте координатора щонайпізніше за 2 години до зміни.\n\n"
"Є питання? Напишіть у WhatsApp на номер, з якого отримали це посилання."),
"es": ("Primer día y contacto",
"El primer día preséntate al coordinador de Find Work en la entrada principal. Lleva tu documento de identidad.\n\n"
"- Vestuario y taquilla: el coordinador te da la llave.\n"
"- Descansos: 15 minutos cada 2 horas, 30 minutos para comer.\n"
"- Avisa de una ausencia al coordinador como mínimo 2 horas antes del turno.\n\n"
"¿Preguntas? Escribe por WhatsApp al número desde el que recibiste este enlace."),
"ru": ("Первый день и контакт",
"В первый день обратитесь к координатору Find Work у главного входа. Возьмите с собой документ, удостоверяющий личность.\n\n"
"- Раздевалка и шкафчик: ключ получите у координатора.\n"
"- Перерывы: 15 минут каждые 2 часа, 30 минут на еду.\n"
"- Об отсутствии сообщайте координатору не позднее чем за 2 часа до смены.\n\n"
"Есть вопросы? Напишите в WhatsApp на номер, с которого получили эту ссылку."),
}

# ---------------------------------------------------------------- Magazyn 2
T[("Magazyn 2", "Bezpieczeństwo w magazynie")] = {
"en": ("Safety in the warehouse",
"In the warehouse the biggest risks are forklift traffic and falling goods.\n\n"
"- Never walk under raised forks.\n"
"- Do not climb the racks. For high shelves use only a forklift or a ladder with someone securing it.\n"
"- Stack pallets up to the height marked on the rack.\n"
"- Report a damaged rack or pallet immediately."),
"uk": ("Безпека на складі",
"На складі найбільший ризик становлять рух навантажувачів і падіння товарів.\n\n"
"- Не проходьте під піднятими вилами.\n"
"- Не залазьте на стелажі. До високих полиць лише навантажувачем або драбиною зі страхуванням.\n"
"- Палети складайте до висоти, позначеної на стелажі.\n"
"- Про пошкоджений стелаж або палету повідомте одразу."),
"es": ("Seguridad en el almacén",
"En el almacén el mayor riesgo es el tráfico de carretillas y la caída de mercancía.\n\n"
"- No pases por debajo de las horquillas elevadas.\n"
"- No subas a las estanterías. A los estantes altos solo con carretilla o con escalera y otra persona asegurando.\n"
"- Apila los palés hasta la altura marcada en la estantería.\n"
"- Avisa de inmediato si una estantería o un palé está dañado."),
"ru": ("Безопасность на складе",
"На складе главный риск составляют движение погрузчиков и падение товаров.\n\n"
"- Не проходите под поднятыми вилами.\n"
"- Не залезайте на стеллажи. К высоким полкам только погрузчиком или лестницей со страховкой.\n"
"- Паллеты складывайте до высоты, обозначенной на стеллаже.\n"
"- О повреждённом стеллаже или паллете сообщите сразу."),
}

T[("Magazyn 2", "Skaner i system WMS")] = {
"en": ("Scanner and the WMS system",
"You confirm every operation with the scanner. Without a scan the goods do not exist in the system.\n\n"
"- Scanner login: your employee number.\n"
"- Picking: scan the location, then the product, then the quantity.\n"
"- Scan error: do not click on, call the shift leader."),
"uk": ("Сканер і система WMS",
"Кожну операцію ви підтверджуєте сканером. Без сканування товару не існує в системі.\n\n"
"- Вхід у сканер: ваш номер працівника.\n"
"- Комплектація: скануйте локацію, потім товар, потім кількість.\n"
"- Помилка сканування: не натискайте далі, покличте лідера зміни."),
"es": ("Escáner y sistema WMS",
"Confirmas cada operación con el escáner. Sin escaneo la mercancía no existe en el sistema.\n\n"
"- Acceso al escáner: tu número de empleado.\n"
"- Picking: escanea la ubicación, después el producto y después la cantidad.\n"
"- Error de escaneo: no sigas, llama al jefe de turno."),
"ru": ("Сканер и система WMS",
"Каждую операцию вы подтверждаете сканером. Без сканирования товара не существует в системе.\n\n"
"- Вход в сканер: ваш номер сотрудника.\n"
"- Комплектация: сканируйте ячейку, затем товар, затем количество.\n"
"- Ошибка сканирования: не нажимайте дальше, позовите лидера смены."),
}

T[("Magazyn 2", "Odzież i obuwie ochronne")] = {
"en": ("Protective clothing and footwear", "S3 safety shoes, high-visibility vest and gloves. In winter an insulated jacket from the warehouse."),
"uk": ("Захисний одяг і взуття", "Взуття S3, світловідбивний жилет і рукавиці. Взимку утеплена куртка зі складу."),
"es": ("Ropa y calzado de protección", "Calzado S3, chaleco reflectante y guantes. En invierno, chaqueta acolchada del almacén."),
"ru": ("Защитная одежда и обувь", "Обувь S3, светоотражающий жилет и перчатки. Зимой утеплённая куртка со склада."),
}

T[("Magazyn 2", "Pierwszy dzień i kontakt")] = {
"en": ("First day and contact", "Report to the shift leader in the warehouse office. You will get a scanner, a locker key and the plan for your first week."),
"uk": ("Перший день і контакт", "Зверніться до лідера зміни в офісі складу. Ви отримаєте сканер, ключ від шафки і план першого тижня."),
"es": ("Primer día y contacto", "Preséntate al jefe de turno en la oficina del almacén. Recibirás un escáner, la llave de la taquilla y el plan de la primera semana."),
"ru": ("Первый день и контакт", "Обратитесь к лидеру смены в офисе склада. Вы получите сканер, ключ от шкафчика и план первой недели."),
}

# ---------------------------------------------------------------- Piekarnia
T[("Piekarnia", "Higiena i strefa produkcji spożywczej")] = {
"en": ("Hygiene and the food production area",
"HACCP rules apply in the bakery. Before entering production:\n\n"
"- Wash and disinfect your hands, put on a hair net and an apron.\n"
"- Jewellery, watch, nail polish: not allowed.\n"
"- Cover a cut with a blue plaster and report it to the leader.\n"
"- Illness (diarrhoea, vomiting, fever): do not come to work, call the coordinator."),
"uk": ("Гігієна та зона харчового виробництва",
"У пекарні діють правила HACCP. Перед входом на виробництво:\n\n"
"- Вимийте і продезінфікуйте руки, одягніть шапочку і фартух.\n"
"- Прикраси, годинник, лак на нігтях: заборонено.\n"
"- Поріз заклейте синім пластиром і повідомте лідера.\n"
"- Хвороба (діарея, блювання, температура): не приходьте на роботу, зателефонуйте координатору."),
"es": ("Higiene y zona de producción alimentaria",
"En la panadería rigen las normas HACCP. Antes de entrar en producción:\n\n"
"- Lávate y desinfecta las manos, ponte el gorro y el delantal.\n"
"- Joyas, reloj, esmalte de uñas: prohibidos.\n"
"- Cubre un corte con una tirita azul y avisa al líder.\n"
"- Enfermedad (diarrea, vómitos, fiebre): no vengas a trabajar, llama al coordinador."),
"ru": ("Гигиена и зона пищевого производства",
"В пекарне действуют правила HACCP. Перед входом на производство:\n\n"
"- Вымойте и продезинфицируйте руки, наденьте шапочку и фартук.\n"
"- Украшения, часы, лак на ногтях: запрещены.\n"
"- Порез заклейте синим пластырем и сообщите лидеру.\n"
"- Болезнь (диарея, рвота, температура): не приходите на работу, позвоните координатору."),
}

T[("Piekarnia", "Bezpieczeństwo przy piecach i krajalnicach")] = {
"en": ("Safety at ovens and slicers",
"- Ovens: open the door with your face turned away, use heat-resistant gloves.\n"
"- Slicer: only after training, never without the guard.\n"
"- Wet floor: wipe it up at once or put out a sign."),
"uk": ("Безпека біля печей і слайсерів",
"- Печі: відкривайте дверцята, відвернувши обличчя, використовуйте термостійкі рукавиці.\n"
"- Слайсер: лише після навчання, ніколи без огорожі.\n"
"- Мокра підлога: одразу витріть або поставте знак."),
"es": ("Seguridad en hornos y cortadoras",
"- Hornos: abre la puerta apartando la cara, usa guantes térmicos.\n"
"- Cortadora: solo tras la formación, nunca sin la protección.\n"
"- Suelo mojado: sécalo enseguida o coloca una señal."),
"ru": ("Безопасность у печей и слайсеров",
"- Печи: открывайте дверцу, отвернув лицо, используйте термостойкие перчатки.\n"
"- Слайсер: только после обучения, никогда без ограждения.\n"
"- Мокрый пол: сразу вытрите или поставьте знак."),
}

T[("Piekarnia", "Pierwszy dzień i kontakt")] = {
"en": ("First day and contact", "The night shift starts at 22:00. Report to the leader at the staff entrance."),
"uk": ("Перший день і контакт", "Нічна зміна починається о 22:00. Зверніться до лідера біля службового входу."),
"es": ("Primer día y contacto", "El turno de noche empieza a las 22:00. Preséntate al líder en la entrada de personal."),
"ru": ("Первый день и контакт", "Ночная смена начинается в 22:00. Обратитесь к лидеру у служебного входа."),
}

# ---------------------------------------------------------------- Back office
T[("Back office", "Zasady pracy w biurze")] = {
"en": ("Office rules",
"- Working hours 8:00 to 16:00, flexible start until 9:00 by agreement.\n"
"- You will receive system access by email on your first day.\n"
"- Personal data of employees and clients: never taken out, never sent to private mailboxes."),
"uk": ("Правила роботи в офісі",
"- Робочий час з 8:00 до 16:00, гнучкий початок до 9:00 за домовленістю.\n"
"- Доступи до систем отримаєте електронною поштою першого дня.\n"
"- Персональні дані працівників і клієнтів: не виносимо, не пересилаємо на приватні скриньки."),
"es": ("Normas de trabajo en la oficina",
"- Horario de 8:00 a 16:00, inicio flexible hasta las 9:00 previo acuerdo.\n"
"- Los accesos a los sistemas los recibirás por correo el primer día.\n"
"- Datos personales de empleados y clientes: no se sacan ni se envían a correos privados."),
"ru": ("Правила работы в офисе",
"- Рабочее время с 8:00 до 16:00, гибкое начало до 9:00 по договорённости.\n"
"- Доступы к системам получите по электронной почте в первый день.\n"
"- Персональные данные сотрудников и клиентов: не выносим, не пересылаем на личную почту."),
}

T[("Back office", "Bezpieczeństwo informacji")] = {
"en": ("Information security",
"- Lock your computer when you leave your desk.\n"
"- Passwords only in the password manager, never on paper.\n"
"- Suspicious email: do not click, forward it to IT."),
"uk": ("Безпека інформації",
"- Блокуйте комп'ютер, коли відходите від столу.\n"
"- Паролі лише в менеджері паролів, ніколи на папері.\n"
"- Підозрілий лист: не натискайте, перешліть до IT."),
"es": ("Seguridad de la información",
"- Bloquea el ordenador cuando te alejes del escritorio.\n"
"- Contraseñas solo en el gestor de contraseñas, nunca en papel.\n"
"- Correo sospechoso: no hagas clic, reenvíalo a IT."),
"ru": ("Информационная безопасность",
"- Блокируйте компьютер, когда отходите от стола.\n"
"- Пароли только в менеджере паролей, никогда на бумаге.\n"
"- Подозрительное письмо: не нажимайте, перешлите в IT."),
}

T[("Back office", "Pierwszy dzień i kontakt")] = {
"en": ("First day and contact", "Report to reception at 9:00. Your first-week buddy will show you around the office."),
"uk": ("Перший день і контакт", "Зверніться до рецепції о 9:00. Наставник першого тижня проведе вас по офісу."),
"es": ("Primer día y contacto", "Preséntate en recepción a las 9:00. Tu tutor de la primera semana te enseñará la oficina."),
"ru": ("Первый день и контакт", "Обратитесь на ресепшен в 9:00. Наставник первой недели проведёт вас по офису."),
}

# Podpisy pod ilustracjami (plik -> {lang: podpis})
CAPTIONS = {
    "hala_demo.png": {
        "en": "Yellow lines mark the pedestrian routes. Red STOP buttons on every machine.",
        "uk": "Жовті лінії позначають пішохідні доріжки. Червоні кнопки STOP на кожній машині.",
        "es": "Las líneas amarillas marcan las vías peatonales. Pulsadores rojos STOP en cada máquina.",
        "ru": "Жёлтые линии обозначают пешеходные дорожки. Красные кнопки STOP на каждой машине.",
    },
    "wylacznik_demo.png": {
        "en": "Emergency stop. Press when you see danger.",
        "uk": "Аварійний вимикач. Натисніть, коли бачите загрозу.",
        "es": "Parada de emergencia. Púlsala cuando veas un peligro.",
        "ru": "Аварийный выключатель. Нажмите, когда видите угрозу.",
    },
}


async def main():
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "find-work"))).scalar_one_or_none()
        if not tenant:
            print("Brak tenanta find-work"); return
        segs = {s.name: s for s in (await db.execute(
            select(OnboardingSegment).where(OnboardingSegment.tenant_id == tenant.id))).scalars().all()}
        added = updated = missing = 0
        for (seg_name, title_pl), langs in T.items():
            seg = segs.get(seg_name)
            mod = None
            if seg:
                mod = (await db.execute(select(OnboardingModule).where(
                    OnboardingModule.segment_id == seg.id, OnboardingModule.title == title_pl))).scalars().first()
            if not mod:
                missing += 1; print(f"BRAK modułu: {seg_name} / {title_pl}"); continue
            existing = {tr.lang: tr for tr in (await db.execute(
                select(OnboardingModuleTranslation).where(OnboardingModuleTranslation.module_id == mod.id))).scalars().all()}
            for lang, (title, body) in langs.items():
                if lang in existing:
                    existing[lang].title, existing[lang].body = title, body; updated += 1
                else:
                    db.add(OnboardingModuleTranslation(module_id=mod.id, lang=lang, title=title, body=body)); added += 1
        import json
        from sqlalchemy import text
        from app.models_onboarding import OnboardingAttachment
        await db.execute(text("ALTER TABLE onboarding_attachments ADD COLUMN IF NOT EXISTS caption_i18n TEXT"))
        caps = 0
        for att in (await db.execute(select(OnboardingAttachment).join(OnboardingModule).join(OnboardingSegment)
                                     .where(OnboardingSegment.tenant_id == tenant.id))).scalars().all():
            if att.filename in CAPTIONS:
                att.caption_i18n = json.dumps(CAPTIONS[att.filename], ensure_ascii=False); caps += 1
        await db.commit()
        print(f"Tłumaczenia: dodane {added}, zaktualizowane {updated}, brakujące moduły {missing}, podpisy {caps}")


if __name__ == "__main__":
    asyncio.run(main())
