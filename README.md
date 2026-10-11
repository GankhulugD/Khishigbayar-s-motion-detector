# MotionCare — Хүний хөдөлгөөн таних системийн веб самбар

MPU6050 + GPS мэдрэгчтэй ESP32-S3 төхөөрөмж өгөгдлөө Wi-Fi-аар серверт **бодит хугацаанд** дамжуулна.
Сервер ML загвараар хөдөлгөөнийг (суух, зогсох, алхах, гүйх, хэвтэх, уналт) ангилж,
үр дүнг **төхөөрөмж (OLED, buzzer)** болон **веб самбар** хоёуланд нь харуулна.

```
ESP32-S3 (MPU6050 + GPS) ──POST /api/ingest──▶ Next.js сервер ──▶ ML ангилагч (2 сек цонх)
        ▲                                          │                    │
        └──── хариу: { label, confidence, alert } ◀┘                    ▼
                                                  Веб самбар ◀── SSE /api/stream
```

## Ажиллуулах

```bash
npm install
cp .env.example .env.local
npm run dev        # http://localhost:3000
```

Төхөөрөмж холбогдоогүй үед `SIMULATE=true` (анхдагч) горим нь бодит мэдрэгчтэй адил дохио үүсгэж,
самбарыг шууд ажиллуулна (дээд талд **DEMO** гэж харагдана). Бодит төхөөрөмж өгөгдөл илгээж эхлэхэд demo урсгал автоматаар зогсоно.

## ESP32-C3 төхөөрөмжийг холбох (бодит хугацаанд)

```
ESP32-C3 (MPU9250 50 Hz) ──Wi-Fi, 250 мс тутам POST /api/ingest──▶ Next.js сервер
        ▲   хариу: { label, confidence, alert } → OLED                │ ML ангилал
        └──────────────────────────────────────────────────────────────┤
                                                   Веб самбар ◀── SSE /api/stream (~250 мс)
```

1. **Сервер:** `npm run dev`. Компьютер ба ESP32-C3 нэг Wi-Fi сүлжээнд байх ёстой.
   Компьютерийн IP хаягийг олох: `ipconfig getifaddr en0` (macOS).
2. **Firmware:** `firmware/motioncare_c3/motioncare_c3.ino` — нэг файл, нэмэлт library хэрэггүй (OLED драйвер дотор нь бий).
   Файлын эхэнд байрлах «ТОХИРГОО» хэсэгт Wi-Fi нэр, нууц үг, компьютерийн IP-г бичнэ.
3. **Arduino IDE:** Boards Manager-ээс «esp32 by Espressif Systems» суулгаж, Board = «ESP32C3 Dev Module»,
   «USB CDC On Boot» = Enabled болгоод Upload хийнэ.
4. Serial Monitor (115200) дээр `[WiFi] холбогдлоо` гарч, OLED дээр **LIVE** гэж гарвал
   веб самбар (`http://localhost:3000`) бодит төхөөрөмжийн өгөгдлийг шууд харуулна (DEMO тэмдэг алга болно).

**Веб дээр шууд (хоцролтгүй) харах:** ESP32 өөрөө `ws://<ESP32-ийн IP>:81` WebSocket сервер нээж, хэмжилт бүрийг (50 Hz) хөтөч рүү шууд илгээнэ
(сервероор дамжихгүй). ESP32 IP-гээ серверт мэдэгддэг тул веб автоматаар холбогдоно; эсвэл «Мэдрэгчийн дохио» картын «IP өөрчлөх»-өөр гараар оруулна
(IP нь Serial Monitor дээр `[WiFi] холбогдлоо: IP ...` гэж гарна). Компьютер ба ESP32 нэг Wi-Fi-д байх ёстой. ML ангилал сервер дээр хэвээр.

Төхөөрөмжгүйгээр турших: `node scripts/fake-device.mjs` — ESP32-C3-ийг дуурайж өгөгдөл илгээнэ.

**Анхаар:** Одоогийн baseline ангилагч мэдрэгчийг бүсэлхийд зүүсэн гэж тооцсон. Бугуйд зүүхэд тэнхлэгийн чиглэл өөр тул
бодит өгөгдөл цуглуулж `ml/train.py`-аар загвар сургах хэрэгтэй.

## Ижил Wi-Fi-д байгаа бүх төхөөрөмжөөс нээх (локал)

`npm run dev` нь бүх сүлжээний интерфейс дээр (`-H 0.0.0.0`) ажиллана. Утас, таблет, өөр компьютерээс
`http://<компьютерийн IP>:3000` эсвэл `http://Gankhulugs-MacBook-Air.local:3000` гэж нээнэ.
`next.config.ts`-ийн `allowedDevOrigins` нь 10.x / 192.168.x / 172.x болон `*.local` хаягийг зөвшөөрсөн.
macOS дээр «Firewall» асаалттай бол `node`-д ирэх холболтыг зөвшөөрнө үү.

## Deploy (Vercel)

Vercel-ийн функцууд санах ой хуваалцдаггүй тул сервер **Upstash Redis**-д төлөвөө хадгална (`lib/server/cloud.ts`).
`KV_REST_API_URL` / `KV_REST_API_TOKEN` орчны хувьсагч байвал автоматаар «үүлэн горим»-д шилжинэ:
ESP32 → `https://<app>.vercel.app/api/ingest` (0.5 сек тутам) → Redis → веб `/api/live`-аас 0.5 сек тутам авна.

1. Кодоо GitHub руу push хийнэ → [vercel.com/new](https://vercel.com/new) → репогоо Import.
2. Project → **Storage** → **Upstash for Redis** (Marketplace) → Create → Connect project.
   Бүс (region) нь Tokyo/Seoul орчим байвал хурдан (функцийн бүс `vercel.json`-д `icn1` = Сөүл).
3. Project → Settings → **Environment Variables**: `DEVICE_API_KEY=<нууц үг>` нэмээд **Redeploy**.
4. Firmware-ийн `SERVER_HOSTS`-д `"https://<app>.vercel.app"` нэмж, `DEVICE_KEY`-г ижил болгоод upload хийнэ.
   Локал компьютерүүдийг жагсаалтад үлдээж болно — ESP32 бүгд рүү нь зэрэг илгээнэ.

Хязгаар (үнэгүй багц): Upstash 500K команд/сар ≈ 1 төхөөрөмж + 1 үзэгчтэй 20+ цаг тасралтгүй урсгал;
Vercel Hobby 1M дуудлага/сар. Илүү хэрэгтэй бол Upstash pay-as-you-go ($0.2 / 100K команд).
HTTPS хуудаснаас хөтөч ESP32 руу `ws://` шууд холбогдож чадахгүй тул deploy хийсэн хувилбарт дохио
сервероор дамжиж ≈0.5–1 сек хоцорно; ижил Wi-Fi дээр локал серверээр (http) нээвэл шууд (WebSocket) харагдана.

## Хуудсууд

| Хуудас | Агуулга |
|---|---|
| `/` Хураангуй | Одоогийн хөдөлгөөн, итгэлцэл, мэдрэгчийн 6 тэнхлэгийн түүхий дохио (50 Hz, шууд осциллограф), ML магадлал, өдрийн идэвхийн цагираг, түүх, GPS байршил, анхааруулга, төхөөрөмжийн төлөв |
| `/history` Түүх | Цаг тутмын хуваарилалт, ангилал тус бүрийн нийт хугацаа, шүүлтүүртэй бүртгэл |
| `/device` Төхөөрөмж | OLED-ийн харагдах байдал, өгөгдлийн урсгал, API баримт бичиг |

## API

| Метод | Зам | Тайлбар |
|---|---|---|
| `POST` | `/api/ingest` | Төхөөрөмж → сервер. Толгой `x-device-key`. Хариуд ангиллын үр дүн (OLED-д) |
| `GET` | `/api/snapshot?device=<id>&compact=1` | Сүүлийн үр дүн (төхөөрөмж татаж авах) |
| `GET` | `/api/snapshot` | Веб самбарын бүрэн төлөв |
| `GET` | `/api/stream` | Server-Sent Events — секунд тутам шинэчлэл |
| `GET` | `/api/history` | Өнөөдрийн цаг тутмын хуваарилалт ба бүртгэл |

Жишээ хүсэлт ба хариу `/device` хуудсанд бий.

## Бүтэц

```
app/                    Next.js App Router (хуудсууд + API route)
components/             UI (карт, график, дүрс)
lib/types.ts            Төхөөрөмж ↔ сервер ↔ веб хоорондын өгөгдлийн гэрээ
lib/server/pipeline.ts  ingest → хадгалах → ангилах → анхааруулга → SSE
lib/server/classifier.ts Classifier интерфейс: baseline + RemoteClassifier (ML үйлчилгээ)
lib/server/store.ts     Repository интерфейс: одоо санах ойд (in-memory)
lib/server/simulator.ts Demo өгөгдөл үүсгэгч
firmware/motioncare_c3/ ESP32-C3 Arduino код (MPU9250, OLED, Wi-Fi → /api/ingest)
scripts/fake-device.mjs Төхөөрөмж дуурайгч (тест)
ml/                     Python: шинж чанар, сургалт (train.py), FastAPI үйлчилгээ (service.py)
```

## Өргөжүүлэх зам

1. **ML загвар** — `ml/data/*.csv`-д шошготой өгөгдөл цуглуулж `python ml/train.py` → `uvicorn service:app --port 8000`,
   дараа нь `.env.local`-д `ML_SERVICE_URL=http://localhost:8000`. Үйлчилгээ унтарвал систем baseline руу автоматаар шилжинэ.
2. **Өгөгдлийн сан** — `lib/server/store.ts` дахь `Repository` интерфейсийг PostgreSQL/TimescaleDB (Prisma, Drizzle)
   эсвэл MongoDB-гоор хэрэгжүүлж `getRepository()`-г солино. Бусад код өөрчлөгдөхгүй.
3. **Бодит хугацааны дамжуулалт** — HTTP-ийн оронд MQTT эсвэл WebSocket ашиглахдаа зөвхөн `ingest()` функцийг дуудна.
4. **Нэвтрэлт ба олон хэрэглэгч** — NextAuth/Clerk, төхөөрөмж ↔ хэрэглэгч ↔ асран хамгаалагчийн холбоос.
5. **Мэдэгдэл** — `pipeline.ts`-ийн уналтын хэсгээс Telegram / SMS / Push мэдэгдэл илгээх.

## Tech stack

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 · Server-Sent Events · (ML) Python, scikit-learn, FastAPI
