# repairs/ml/balance_model.py

def recommend_warehouse():
    from repairs.models import Warehouse, RepairJob

    warehouses = Warehouse.objects.all()
    loads = []

    for w in warehouses:
        load = RepairJob.objects.filter(
            warehouse=w,
            status__in=["received", "repairing"]
        ).count()

        loads.append((w.name, load))
    if not loads:
        return {"warehouse": None, "load": 0, "all_warehouses": []}

    sorted_warehouses = sorted(loads, key=lambda x: x[1])
    best = sorted_warehouses[0]  # lowest load

    return {
        "warehouse": best[0],
        "load": best[1],
        "all_warehouses": loads
    }
