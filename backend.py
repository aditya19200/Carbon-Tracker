import os
from typing import Optional, Tuple, List, Dict, Any
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.pool = pooling.MySQLConnectionPool(
            pool_name="carbon_pool",
            pool_size=5,
            pool_reset_session=True,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "carbon_tracker"),
            autocommit=True,
        )

    def _conn(self):
        return self.pool.get_connection()

    # ---------- Master data ----------
    def list_users(self):
        q = "SELECT UserID, Name, Email, CarbonGoal, RegistrationDate FROM Users ORDER BY UserID"
        with self._conn() as cn, cn.cursor(dictionary=True) as cur:
            cur.execute(q)
            return cur.fetchall()

    def add_user(self, name: str, email: str, password: str, carbon_goal: Optional[float], reg_date: str):
        q = """INSERT INTO Users (Name, Email, Password, CarbonGoal, RegistrationDate)
               VALUES (%s,%s,%s,%s,%s)"""
        with self._conn() as cn, cn.cursor() as cur:
            cur.execute(q, (name, email, password, carbon_goal, reg_date))
            return cur.lastrowid

    def list_activities(self):
        q = """SELECT A.ActivityID, A.Name, A.UnitOfMeasure, C.CategoryName, EF.EmissionValue
               FROM Activities A
               JOIN Categories C ON A.CategoryID=C.CategoryID
               LEFT JOIN EmissionFactors EF ON EF.ActivityID=A.ActivityID
               ORDER BY A.ActivityID"""
        with self._conn() as cn, cn.cursor(dictionary=True) as cur:
            cur.execute(q)
            return cur.fetchall()

    def list_locations(self):
        q = "SELECT LocationID, City, Country FROM Locations ORDER BY City"
        with self._conn() as cn, cn.cursor(dictionary=True) as cur:
            cur.execute(q)
            return cur.fetchall()

    # ---------- Logs (CRUD-lite) ----------
    def list_logs(self, user_id: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None):
        base = """SELECT AL.LogID, U.Name AS UserName, A.Name AS ActivityName, 
                         AL.Date, AL.Quantity, AL.CalculatedEmission, L.City, L.Country
                  FROM ActivityLogs AL
                  JOIN Users U ON U.UserID=AL.UserID
                  JOIN Activities A ON A.ActivityID=AL.ActivityID
                  LEFT JOIN Locations L ON L.LocationID=AL.LocationID
                  WHERE 1=1"""
        args: List[Any] = []
        if user_id:
            base += " AND AL.UserID=%s"
            args.append(user_id)
        if date_from:
            base += " AND AL.Date >= %s"
            args.append(date_from)
        if date_to:
            base += " AND AL.Date <= %s"
            args.append(date_to)
        base += " ORDER BY AL.Date DESC, AL.LogID DESC"
        with self._conn() as cn, cn.cursor(dictionary=True) as cur:
            cur.execute(base, tuple(args))
            return cur.fetchall()

    def add_log(self, user_id: int, activity_id: int, date: str, qty: float,
                location_id: Optional[int] = None):
        # Emission is auto-computed by BEFORE INSERT trigger in your schema
        q = """INSERT INTO ActivityLogs (UserID, ActivityID, LocationID, Date, Quantity)
               VALUES (%s,%s,%s,%s,%s)"""
        with self._conn() as cn, cn.cursor() as cur:
            cur.execute(q, (user_id, activity_id, location_id, date, qty))
            return cur.lastrowid

    def delete_log(self, log_id: int):
        with self._conn() as cn, cn.cursor() as cur:
            cur.execute("DELETE FROM ActivityLogs WHERE LogID=%s", (log_id,))
            return cur.rowcount

    # ---------- Procedures / Functions ----------
    def monthly_emissions_by_category(self, user_id: int, year: int, month: int):
        # CALL GetMonthlyEmissionsByCategory(IN p_user_id, IN p_year, IN p_month)
        with self._conn() as cn, cn.cursor(dictionary=True) as cur:
            cur.callproc("GetMonthlyEmissionsByCategory", [user_id, year, month])
            # mysql-connector exposes results via stored_results()
            results = []
            for r in cur.stored_results():
                results = r.fetchall()
            return results

    def activity_ranking(self, user_id: int, start_date: str, end_date: str):
        with self._conn() as cn, cn.cursor(dictionary=True) as cur:
            cur.callproc("GetActivityRankingByEmission", [user_id, start_date, end_date])
            results = []
            for r in cur.stored_results():
                results = r.fetchall()
            return results

    def user_met_goal(self, user_id: int, year: int, month: int) -> Optional[bool]:
        with self._conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT CheckIfUserMetGoal(%s,%s,%s)", (user_id, year, month))
            row = cur.fetchone()
            return bool(row[0]) if row else None
