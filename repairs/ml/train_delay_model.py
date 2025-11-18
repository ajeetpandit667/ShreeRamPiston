# repairs/ml/train_delay_model.py

import os
import django
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Repair.settings")
django.setup()

from repairs.models import RepairJob, Warehouse


def train_model():
    jobs = RepairJob.objects.all()

    if len(jobs) < 10:
        print("Not enough data to train model.")
        return

    data = []

    for j in jobs:
        warehouse_load = RepairJob.objects.filter(
            store=j.store, status__in=["received", "repairing"]
        ).count()

        vendor_load = RepairJob.objects.filter(status="sent_vendor").count()

        label = 1 if j.delivery_date and j.delivery_date < j.updated_at.date() else 0

        data.append([
            j.repair_days,
            warehouse_load,
            vendor_load,
            j.damage_reason,
            label
        ])

    df = pd.DataFrame(data, columns=[
        "repair_days", "warehouse_load", "vendor_load", "damage", "delayed"
    ])

    # NLP Vectorizer
    vectorizer = TfidfVectorizer(max_features=100)
    damage_features = vectorizer.fit_transform(df["damage"].fillna(""))

    X_numeric = df[["repair_days", "warehouse_load", "vendor_load"]].values
    X = np.hstack([X_numeric, damage_features.toarray()])
    y = df["delayed"]

    model = RandomForestClassifier()
    model.fit(X, y)

    joblib.dump(model, "delay_model.pkl")
    joblib.dump(vectorizer, "damage_vectorizer.pkl")

    print("Model trained and saved!")


if __name__ == "__main__":
    train_model()
