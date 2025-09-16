import logging
import matplotlib.pyplot as plt
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

    full_buy_df = pd.DataFrame([])
    full_sell_df = pd.DataFrame([])

    #for i in range(0,len(item_list)):
    for i in range(0,len(item_list)):
        time.sleep(0.1)
        if i%10 == 0:
            logging.info(f"{np.round(100*i/len(item_list),2)}% Complete, {i:,}/{len(item_list):,}")
        entry = item_list[i]
        
        # Get market info for the given item
        item_name = entry["name"]
        item_id = entry["id"]
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

        # Load buy/sell orders into dataframes
        buy_orders = market["buyOrders"]
        sell_orders = market["sellOrders"]
        buy_df = pd.DataFrame(buy_orders)
        sell_df = pd.DataFrame(sell_orders)

        full_buy_df = pd.concat([full_buy_df,buy_df],ignore_index=True)
        full_sell_df = pd.concat([full_sell_df,sell_df],ignore_index=True)

    # Initialize the bar plot
    plt.style.use("Solarize_Light2")
    fig, axs = plt.subplots(2,figsize=(10,6))

    N_top = 10

    # Plot the quantity of stored coins in the markets
    full_buy_df["storedCoins"] = full_buy_df["storedCoins"].astype(int)
    full_buy_df = full_buy_df[["claimEntityId","claimName","storedCoins"]]
    full_buy_df = full_buy_df.groupby(["claimEntityId","claimName"],as_index=False).sum()
    full_buy_df = full_buy_df.sort_values(by="storedCoins",ascending=False).reset_index(drop=True)
    top_buyers = full_buy_df.head(N_top)
    buy_names = list(top_buyers["claimName"])+["All Other Markets"]
    buy_values = list(top_buyers["storedCoins"]) + [int(full_buy_df["storedCoins"].sum()-top_buyers["storedCoins"].sum())]
    full_buy_df.index += 1
    logging.info(f"Buy Order Ranking\n{full_buy_df["claimName"].to_string()}")

    axs[0].bar(buy_names,buy_values)
    axs[0].tick_params(axis='x', labelrotation=20, labelsize=5)
    axs[0].set_ylabel("Total Ħ in Buy Orders")
    axs[0].ticklabel_format(axis="y",style="sci",scilimits=(0,0))
    axs[0].get_yaxis().get_offset_text().set_position((-0.05,0.5))

    # Plot the quantity of stored goods in the markets
    full_sell_df["quantity"] = full_sell_df["quantity"].astype(int)
    full_sell_df = full_sell_df[["claimEntityId","claimName","quantity"]]
    full_sell_df = full_sell_df.groupby(["claimEntityId","claimName"],as_index=False).sum()
    full_sell_df = full_sell_df.sort_values(by="quantity",ascending=False).reset_index(drop=True)
    top_sellers = full_sell_df.head(N_top)
    sell_names = list(top_sellers["claimName"])+["All Other Markets"]
    sell_values = list(top_sellers["quantity"]) + [int(full_sell_df["quantity"].sum()-top_sellers["quantity"].sum())]
    full_sell_df.index += 1
    logging.info(f"Sell Order Ranking\n{full_sell_df["claimName"].to_string()}")

    axs[1].bar(sell_names,sell_values)
    axs[1].tick_params(axis='x', labelrotation=20, labelsize=5)
    axs[1].set_ylabel("Total Goods in Sell Orders")
    axs[1].ticklabel_format(axis="y",style="sci",scilimits=(0,0))
    axs[1].get_yaxis().get_offset_text().set_position((-0.05,0.5))

    axs[0].set_title("BitCraft Online Market Sizes")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Initialize logging to both console and log file
    logging.basicConfig(
        # level=logging.DEBUG,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("world_markets.log", mode="w"),
        ],
        force=True,
    )
    logging.info("===== BitCraft World Market Compare Starting =====")
    main()
    logging.info("=== BitCraft World Market Compare Shutting Down ===")
    logging.shutdown()