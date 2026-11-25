"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/producer/event_generator.py

Realistic synthetic event data generator for Kafka producer testing.

Generates three event types commonly used in real-time data pipelines:
  1. Sales/Order events       — e-commerce order lifecycle
  2. User clickstream events  — web/app behavioral analytics
  3. IoT sensor readings      — industrial/smart device telemetry

Business Use Case:
  When building Kafka pipelines, you need realistic test data that mirrors
  production volume and schema complexity. This generator creates events
  with realistic distributions, correlations, and cardinalities.

Interview Questions:
  Q: How do you test Kafka pipelines without a live data source?
  A: Use a synthetic event generator that matches the production schema
     and statistical properties (cardinality, null rates, value distributions).
     This lets you run load tests and validate processing logic before go-live.

  Q: What makes test data "realistic" for a data pipeline?
  A: 1. Correct schema/types, 2. Realistic value distributions (not uniform),
     3. Correct cardinality (10K users, 1K products), 4. Edge cases (nulls,
     special chars, extremes), 5. Temporal patterns (peak hours, weekday vs weekend)
"""

import random
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Generator, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Reference Data (realistic cardinalities)
# ─────────────────────────────────────────────────────────────────────────────

_PRODUCT_CATALOG = [
    {"product_id": f"PROD-{i:04d}", "name": name, "category": cat, "price": price}
    for i, (name, cat, price) in enumerate([
        ("Wireless Headphones Pro", "Electronics", 149.99),
        ("Ergonomic Office Chair", "Furniture", 399.99),
        ("Running Shoes X1", "Footwear", 89.99),
        ("Organic Coffee Beans 1kg", "Grocery", 24.99),
        ("Python Programming Book", "Books", 49.99),
        ("Yoga Mat Premium", "Sports", 39.99),
        ("Smart Watch Series 5", "Electronics", 299.99),
        ("Standing Desk 140cm", "Furniture", 599.99),
        ("Mechanical Keyboard TKL", "Electronics", 129.99),
        ("Water Bottle 1L BPA-Free", "Sports", 19.99),
        ("Noise Cancelling Earbuds", "Electronics", 79.99),
        ("LED Desk Lamp 12W", "Home", 34.99),
        ("Protein Powder Vanilla 2kg", "Health", 59.99),
        ("JavaScript: The Good Parts", "Books", 34.99),
        ("Gaming Mouse 16000DPI", "Electronics", 69.99),
        ("Air Fryer 5.5L", "Appliances", 119.99),
        ("Resistance Bands Set", "Sports", 29.99),
        ("Bamboo Cutting Board", "Kitchen", 22.99),
        ("Foam Roller Deep Tissue", "Health", 28.99),
        ("USB-C Hub 7-in-1", "Electronics", 45.99),
    ])
]

_USER_POOL_SIZE = 50_000   # Realistic active user base
_REGIONS = ["us-east", "us-west", "eu-west", "eu-central", "apac", "latam"]
_CHANNELS = ["web", "mobile-ios", "mobile-android", "tablet", "smart-tv"]
_PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay", "crypto"]
_ORDER_STATUSES = ["placed", "confirmed", "processing", "shipped", "delivered", "cancelled"]
_SENSOR_TYPES = ["temperature", "humidity", "pressure", "vibration", "co2", "power_consumption"]
_DEVICE_MANUFACTURERS = ["SensorTech", "IoTMaster", "SmartEdge", "DataSense", "AquaMetrics"]
_PAGE_TYPES = ["home", "category", "product_detail", "search", "cart", "checkout", "account", "blog"]
_UTM_SOURCES = ["google", "facebook", "email", "organic", "direct", "instagram", "tiktok"]
_UTM_MEDIUMS = ["cpc", "social", "email", "organic", "display"]


# ─────────────────────────────────────────────────────────────────────────────
# Event Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OrderItem:
    product_id: str
    product_name: str
    category: str
    unit_price: float
    quantity: int
    discount_pct: float
    line_total: float


@dataclass
class SaleEvent:
    """Represents a sales/order lifecycle event."""
    event_id: str
    event_type: str           # placed, confirmed, shipped, etc.
    order_id: str
    user_id: str
    session_id: str
    region: str
    channel: str
    payment_method: str
    currency: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    shipping_fee: float
    discount_amount: float
    total_amount: float
    is_first_order: bool
    coupon_code: Optional[str]
    event_timestamp: str
    server_timestamp: str


@dataclass
class ClickEvent:
    """Represents a user clickstream/behavioral event."""
    event_id: str
    event_type: str           # page_view, click, scroll, add_to_cart, search
    user_id: Optional[str]   # None = anonymous/guest user
    session_id: str
    anonymous_id: str
    page_url: str
    page_type: str
    referrer_url: Optional[str]
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]
    device_type: str
    browser: str
    os: str
    country: str
    region: str
    element_id: Optional[str]
    search_query: Optional[str]
    product_id: Optional[str]
    session_duration_s: int
    scroll_depth_pct: int
    event_timestamp: str


@dataclass
class IoTReading:
    """Represents an IoT sensor telemetry reading."""
    reading_id: str
    device_id: str
    device_name: str
    sensor_type: str
    manufacturer: str
    site_id: str
    floor: int
    zone: str
    value: float
    unit: str
    quality: str             # good, degraded, bad
    battery_level: int       # 0-100%
    firmware_version: str
    latitude: float
    longitude: float
    alert_triggered: bool
    alert_threshold: Optional[float]
    event_timestamp: str


# ─────────────────────────────────────────────────────────────────────────────
# Event Generator
# ─────────────────────────────────────────────────────────────────────────────

class EventGenerator:
    """
    Realistic synthetic event generator for Kafka load testing and development.

    Usage:
        gen = EventGenerator(seed=42)  # seed for reproducibility

        # Single events
        sale = gen.generate_sale()
        click = gen.generate_click()
        reading = gen.generate_iot_reading()

        # Streaming generators
        for event in gen.stream_sales(rate_per_sec=1000, duration_sec=60):
            producer.produce_event("sales-events", event)
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._order_counter = 1_000_000

    # ──────────────────────────────────────────────
    # Sales Events
    # ──────────────────────────────────────────────

    def generate_sale(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a realistic e-commerce order event.

        Event types follow the order lifecycle:
        placed → confirmed → processing → shipped → delivered (or cancelled)
        """
        evt_type = event_type or self._rng.choice(
            ["placed"] * 5 + ["confirmed"] * 3 + ["shipped"] * 2 + ["delivered"] * 2
        )

        uid = user_id or f"USR-{self._rng.randint(1, _USER_POOL_SIZE):06d}"
        order_id = f"ORD-{self._order_counter:010d}"
        self._order_counter += 1

        # Generate 1–5 items per order (weighted toward 1-2 items)
        num_items = self._rng.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
        selected = self._rng.sample(_PRODUCT_CATALOG, min(num_items, len(_PRODUCT_CATALOG)))

        items = []
        subtotal = 0.0
        for product in selected:
            qty = self._rng.choices([1, 2, 3], weights=[70, 20, 10])[0]
            discount_pct = self._rng.choices(
                [0, 5, 10, 15, 20, 25], weights=[50, 15, 15, 10, 7, 3]
            )[0]
            unit_price = product["price"]
            line_total = round(unit_price * qty * (1 - discount_pct / 100), 2)
            subtotal += line_total

            items.append(asdict(OrderItem(
                product_id=product["product_id"],
                product_name=product["name"],
                category=product["category"],
                unit_price=unit_price,
                quantity=qty,
                discount_pct=float(discount_pct),
                line_total=line_total,
            )))

        subtotal = round(subtotal, 2)
        tax = round(subtotal * 0.085, 2)          # 8.5% tax rate
        shipping_fee = round(self._rng.uniform(0, 15), 2) if subtotal < 50 else 0.0
        discount_amount = round(subtotal * self._rng.uniform(0, 0.1), 2)
        total_amount = round(subtotal + tax + shipping_fee - discount_amount, 2)

        coupon_code = None
        if self._rng.random() < 0.15:  # 15% of orders use a coupon
            coupon_code = f"SAVE{self._rng.choice([5, 10, 15, 20])}"

        event = SaleEvent(
            event_id=str(uuid.uuid4()),
            event_type=evt_type,
            order_id=order_id,
            user_id=uid,
            session_id=f"SES-{uuid.uuid4().hex[:12]}",
            region=self._rng.choice(_REGIONS),
            channel=self._rng.choice(_CHANNELS),
            payment_method=self._rng.choice(_PAYMENT_METHODS),
            currency="USD",
            items=items,
            subtotal=subtotal,
            tax=tax,
            shipping_fee=shipping_fee,
            discount_amount=discount_amount,
            total_amount=total_amount,
            is_first_order=self._rng.random() < 0.12,  # 12% are first-time buyers
            coupon_code=coupon_code,
            event_timestamp=datetime.now(timezone.utc).isoformat(),
            server_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return asdict(event)

    # ──────────────────────────────────────────────
    # Clickstream Events
    # ──────────────────────────────────────────────

    def generate_click(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a realistic user clickstream/behavioral event."""
        page_type = self._rng.choice(_PAGE_TYPES)
        is_authenticated = self._rng.random() < 0.6  # 60% logged-in users

        uid = user_id if is_authenticated else None
        if is_authenticated and not uid:
            uid = f"USR-{self._rng.randint(1, _USER_POOL_SIZE):06d}"

        event_type_weights = {
            "page_view": 50,
            "click": 25,
            "scroll": 15,
            "add_to_cart": 5,
            "search": 4,
            "remove_from_cart": 1,
        }
        evt_type = self._rng.choices(
            list(event_type_weights.keys()),
            weights=list(event_type_weights.values())
        )[0]

        # Construct realistic URL based on page type
        base_url = "https://shop.example.com"
        url_map = {
            "home": f"{base_url}/",
            "category": f"{base_url}/category/{self._rng.choice(['electronics', 'furniture', 'sports'])}",
            "product_detail": f"{base_url}/product/{self._rng.choice(_PRODUCT_CATALOG)['product_id'].lower()}",
            "search": f"{base_url}/search?q={self._rng.choice(['headphones', 'chair', 'laptop'])}",
            "cart": f"{base_url}/cart",
            "checkout": f"{base_url}/checkout",
            "account": f"{base_url}/account/orders",
            "blog": f"{base_url}/blog/{self._rng.randint(1, 500)}",
        }

        has_utm = self._rng.random() < 0.3
        country_code = self._rng.choice(["US", "GB", "DE", "FR", "AU", "CA", "IN", "BR", "JP"])

        product_id = None
        if page_type == "product_detail":
            product_id = self._rng.choice(_PRODUCT_CATALOG)["product_id"]

        event = ClickEvent(
            event_id=str(uuid.uuid4()),
            event_type=evt_type,
            user_id=uid,
            session_id=session_id or f"SES-{uuid.uuid4().hex[:12]}",
            anonymous_id=f"ANON-{uuid.uuid4().hex[:16]}",
            page_url=url_map.get(page_type, base_url),
            page_type=page_type,
            referrer_url=f"https://www.google.com" if self._rng.random() < 0.3 else None,
            utm_source=self._rng.choice(_UTM_SOURCES) if has_utm else None,
            utm_medium=self._rng.choice(_UTM_MEDIUMS) if has_utm else None,
            utm_campaign=f"campaign-{self._rng.randint(1, 50)}" if has_utm else None,
            device_type=self._rng.choice(["desktop", "mobile", "tablet"]),
            browser=self._rng.choice(["Chrome", "Safari", "Firefox", "Edge"]),
            os=self._rng.choice(["Windows", "macOS", "iOS", "Android", "Linux"]),
            country=country_code,
            region=self._rng.choice(_REGIONS),
            element_id=f"btn-{self._rng.choice(['add-cart', 'buy-now', 'nav-menu', 'search-bar'])}" if evt_type == "click" else None,
            search_query=self._rng.choice(["laptop", "headphones", "chair"]) if evt_type == "search" else None,
            product_id=product_id,
            session_duration_s=self._rng.randint(5, 3600),
            scroll_depth_pct=self._rng.randint(10, 100),
            event_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return asdict(event)

    # ──────────────────────────────────────────────
    # IoT Sensor Events
    # ──────────────────────────────────────────────

    def generate_iot_reading(
        self,
        device_id: Optional[str] = None,
        sensor_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a realistic IoT sensor telemetry reading."""
        s_type = sensor_type or self._rng.choice(_SENSOR_TYPES)
        did = device_id or f"DEV-{self._rng.randint(1, 10000):05d}"

        # Sensor-specific value ranges and units
        sensor_config = {
            "temperature":       (18.0,  45.0,  "°C",   40.0),
            "humidity":          (20.0,  95.0,  "%RH",  80.0),
            "pressure":          (950.0, 1050.0, "hPa", 1020.0),
            "vibration":         (0.0,   10.0,  "mm/s", 7.0),
            "co2":               (350.0, 5000.0,"ppm",  1000.0),
            "power_consumption": (0.0,   500.0, "W",    400.0),
        }

        lo, hi, unit, alert_thresh = sensor_config.get(
            s_type, (0.0, 100.0, "units", 90.0)
        )

        # Simulate realistic distributions (mostly normal range, occasional anomalies)
        if self._rng.random() < 0.05:  # 5% anomalies
            value = round(hi * self._rng.uniform(0.95, 1.1), 3)  # Over threshold
        else:
            value = round(self._rng.uniform(lo, hi * 0.85), 3)

        alert_triggered = value > alert_thresh

        # Simulate degrading battery (older devices have lower battery)
        battery = self._rng.choices(
            range(0, 101),
            weights=[1 if b < 10 else (2 if b < 20 else 1) for b in range(0, 101)]
        )[0]

        # Signal quality correlates with battery level
        if battery < 10 or self._rng.random() < 0.02:
            quality = "bad"
        elif battery < 25 or self._rng.random() < 0.08:
            quality = "degraded"
        else:
            quality = "good"

        # Random coordinates for device location (within a campus)
        base_lat, base_lon = 37.7749, -122.4194  # San Francisco
        lat = round(base_lat + self._rng.uniform(-0.01, 0.01), 6)
        lon = round(base_lon + self._rng.uniform(-0.01, 0.01), 6)

        event = IoTReading(
            reading_id=str(uuid.uuid4()),
            device_id=did,
            device_name=f"{self._rng.choice(_DEVICE_MANUFACTURERS)}-{s_type.upper()}-{did[-4:]}",
            sensor_type=s_type,
            manufacturer=self._rng.choice(_DEVICE_MANUFACTURERS),
            site_id=f"SITE-{self._rng.randint(1, 50):03d}",
            floor=self._rng.randint(1, 20),
            zone=self._rng.choice(["HVAC", "Office", "Server-Room", "Lobby", "Warehouse"]),
            value=value,
            unit=unit,
            quality=quality,
            battery_level=battery,
            firmware_version=f"{self._rng.randint(1, 5)}.{self._rng.randint(0, 9)}.{self._rng.randint(0, 99)}",
            latitude=lat,
            longitude=lon,
            alert_triggered=alert_triggered,
            alert_threshold=alert_thresh if alert_triggered else None,
            event_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return asdict(event)

    # ──────────────────────────────────────────────
    # Streaming Generators (Python Generators)
    # ──────────────────────────────────────────────

    def stream_sales(
        self,
        count: Optional[int] = None,
        duration_sec: Optional[float] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Infinite or bounded stream of sales events.

        Args:
            count:        Stop after N events (None = infinite)
            duration_sec: Stop after N seconds (None = infinite)

        Usage:
            # Infinite stream
            for event in gen.stream_sales():
                producer.produce_event("sales-events", event)

            # Bounded by count
            events = list(gen.stream_sales(count=1000))
        """
        import time
        start = time.monotonic()
        produced = 0

        while True:
            if count and produced >= count:
                break
            if duration_sec and (time.monotonic() - start) >= duration_sec:
                break
            yield self.generate_sale()
            produced += 1

    def stream_clicks(self, count: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        """Infinite or bounded stream of clickstream events."""
        produced = 0
        while True:
            if count and produced >= count:
                break
            yield self.generate_click()
            produced += 1

    def stream_iot(
        self,
        num_devices: int = 100,
        count: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Simulate multiple IoT devices sending readings.

        Devices rotate through sensor types for realistic multi-sensor simulation.
        """
        device_ids = [f"DEV-{i:05d}" for i in range(1, num_devices + 1)]
        produced = 0
        while True:
            if count and produced >= count:
                break
            device_id = self._rng.choice(device_ids)
            yield self.generate_iot_reading(device_id=device_id)
            produced += 1

    def generate_mixed_batch(self, size: int = 1000) -> List[Dict[str, Any]]:
        """
        Generate a mixed batch of events across all types.
        Realistic distribution: 60% clicks, 30% sales, 10% IoT.
        """
        events = []
        sales_count = int(size * 0.30)
        click_count = int(size * 0.60)
        iot_count = size - sales_count - click_count

        events.extend(
            {"type": "sale", "topic": "sales-events", "data": self.generate_sale()}
            for _ in range(sales_count)
        )
        events.extend(
            {"type": "click", "topic": "user-clicks", "data": self.generate_click()}
            for _ in range(click_count)
        )
        events.extend(
            {"type": "iot", "topic": "iot-readings", "data": self.generate_iot_reading()}
            for _ in range(iot_count)
        )

        # Shuffle to simulate interleaved real-world arrival
        self._rng.shuffle(events)
        return events
