import logging
import numpy as np
import pandas as pd
import sys
import time

from main import bitjita_client

def main():
    # Initialize Bitjita API client
    data_client = bitjita_client()

    logging.info("Getting list of items on the global market.")
    item_list = data_client._make_request("market?hasOrders=true&hasBuyOrders=true&hasSellOrders=true")["data"]["items"]

    # Generating report
    report_list = []
    for j in range(0,len(item_list)):
        time.sleep(0.1)
        if j%10 == 0:
            logging.info(f"{np.round(100*j/len(item_list),2)}% Complete, {j:,}/{len(item_list):,}")

        entry = item_list[j]
        # Do the trimming that somehow makes it past the API
        if not entry["hasBuyOrders"]:
            continue
        if not entry["hasSellOrders"]:
            continue

        item_name = entry["name"]
        item_id = entry["id"]

        # Get market info for the given item
        if entry["itemType"]==0:
            item_type = "item"
        elif entry["itemType"]==1:
            item_type = "cargo"
        else:
            continue
        try:
            market = data_client._make_request(f"market/{item_type}/{item_id}")
        except:
            logging.error(f"Error querying bitjita for {item_type} {item_name}")
            time.sleep(10)
            continue

        # Load buy/sell orders into sorted dataframes
        buy_orders = market["buyOrders"]
        sell_orders = market["sellOrders"]
        buy_df = pd.DataFrame(buy_orders)
        sell_df = pd.DataFrame(sell_orders)
        buy_df["priceThreshold"] = buy_df["priceThreshold"].astype(int)
        sell_df["priceThreshold"] = sell_df["priceThreshold"].astype(int)
        buy_df["quantity"] = buy_df["quantity"].astype(int)
        sell_df["quantity"] = sell_df["quantity"].astype(int)
        buy_df = buy_df.sort_values(by="priceThreshold",ascending=False).reset_index(drop=True)
        sell_df = sell_df.sort_values(by="priceThreshold",ascending=True).reset_index(drop=True)

        # OPTIONAL
        # Trim down to just the local region
        region_trim = True
        if region_trim:
            buy_df = buy_df[buy_df["regionName"]=="Draxionne"].reset_index(drop=True)
            sell_df = sell_df[sell_df["regionName"]=="Draxionne"].reset_index(drop=True)

        # Build cumulative buy/sell arrays
        buy_diff = np.array([0])
        for i in range(0,len(buy_df)):
            buy_span = buy_df.iloc[i]["priceThreshold"]*np.ones(buy_df.iloc[i]["quantity"])
            buy_diff = np.concatenate((buy_diff,buy_span))

        sell_diff = np.array([0])
        for i in range(0,len(sell_df)):
            sell_span = sell_df.iloc[i]["priceThreshold"]*np.ones(sell_df.iloc[i]["quantity"])
            sell_diff = np.concatenate((sell_diff,sell_span))

        # Find the market distribution "slack"
        min_size = min(buy_diff.size, sell_diff.size)
        buy_diff = buy_diff[:min_size]
        sell_diff = sell_diff[:min_size]
        profit_diff = buy_diff-sell_diff
        quantity = np.where(profit_diff>=0)[0][-1]
        buy_diff = buy_diff[:quantity+1]
        sell_diff = sell_diff[:quantity+1]
        profit_diff = profit_diff[:quantity+1]

        report_list.append({
            "name": item_name,
            "item_type": item_type,
            "quantity": quantity,
            "max_sellOrder": int(sell_diff[-1]),
            "min_buyOrder": int(buy_diff[-1]),
            "total_spend": int(np.sum(sell_diff)),
            "total_income": int(np.sum(buy_diff)),
            "total_profit": int(np.sum(profit_diff)),
        })

    report_df = pd.DataFrame(report_list)

    # Trim out any items that are merely not unprofitable, rather than positively profitable
    report_df = report_df[report_df["total_profit"]>0]
    report_df = report_df.sort_values(by="total_profit",ascending=False)

    report_df.to_csv("report.csv",index=False)

if __name__ == "__main__":
    # Initialize logging to both console and log file
    logging.basicConfig(
        # level=logging.DEBUG,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bitcraft-sd.log", mode="w"),
        ],
        force=True,
    )
    logging.info("===== BitCraft Supply-Demand Report Generator Starting =====")
    main()
    logging.info("=== BitCraft Supply-Demand Report Generator Shutting Down ===")
    logging.shutdown()