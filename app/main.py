import configparser
import logging
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import sys

np.seterr(divide="ignore", invalid="ignore")

def main():
    # Grabbing config info
    config = configparser.ConfigParser()
    config.read("config.ini")
    item_type = config["Target"]["item_type"]
    item_id = config["Target"]["item_id"]
    region = config["Focus"]["region"]
    claim_id = config["Focus"]["claim_id"]
    claim_name = config["Focus"]["claim_name"]
    logging.info(f"Focusing on {region} region.")
    logging.info(f"Focusing on claim {claim_name} (id: {claim_id}).")

    # Initialize Bitjita API client
    data_client = bitjita_client()

    # Loading target data
    target = data_client._make_request(f"market/{item_type}/{item_id}")
    target_name = target["item"]["name"]
    target_volume = int(target["item"]["volume"])
    buy_orders = target.get("buyOrders",[])
    sell_orders = target.get("sellOrders",[])
    logging.info(f"Target product identified as {item_type}: {target_name}")

    # Calculate how much can fit in a Clipper w/ empty player inventory
    player_slots = 0;   player_slot_size = 0
    boat_slots = 0;     boat_slot_size = 0
    if item_type == "item":
        player_slots = 25
        boat_slots = 30

        player_slot_size = 6000
        boat_slot_size = 6000
    elif item_type == "cargo":
        player_slots = 1
        boat_slots = 6
        
        player_slot_size = 6000
        boat_slot_size = 60000
    if target_volume == 0:
        capacity = np.inf
    else:
        capacity = (player_slots*int(player_slot_size/target_volume)) + (boat_slots*int(boat_slot_size/target_volume))
    logging.info(f"Clipper Capacity of {capacity:,}") 

    # Loading data into DataFrames
    buy_df = pd.DataFrame(buy_orders)
    sell_df = pd.DataFrame(sell_orders)

    if len(buy_df) == 0:
        buy_df = None
    if len(sell_df) == 0:
        sell_df = None

    # Making some stuff into integers and sorting
    if buy_df is not None:
        buy_df["priceThreshold"] = buy_df["priceThreshold"].astype(int)
        buy_df["quantity"] = buy_df["quantity"].astype(int)
        buy_df = buy_df.sort_values(by="priceThreshold",ascending=False).reset_index(drop=True)
    
    if sell_df is not None:
        sell_df["priceThreshold"] = sell_df["priceThreshold"].astype(int)
        sell_df["quantity"] = sell_df["quantity"].astype(int)
        sell_df = sell_df.sort_values(by="priceThreshold",ascending=True).reset_index(drop=True)

    # Initializing the plot
    plt.style.use("Solarize_Light2")
    fig, ax0 = plt.subplots(figsize=(10,6))
    # ax1 = ax0.twinx()
    # ax2 = ax0.twinx()
    # ax2.spines['right'].set_position(('outward', 60))
    lines = []

    # Making the detailed price lines
    if buy_df is not None:
        logging.info("Building global demand curve.")
        global_buy_q, global_buy_ptot = price_line_builder(buy_df)
        GD = ax0.plot(global_buy_ptot/global_buy_q,
                    global_buy_q,
                    color="red",
                    alpha=0.2,
                    label="Global Demand")
        lines += GD

        region_buy_df = buy_df[buy_df["regionName"]==region].reset_index(drop=True)
        if len(region_buy_df) > 0:
            logging.info(f"Building {region} demand curve.")
            region_buy_q, region_buy_ptot = price_line_builder(region_buy_df)
            RD = ax0.plot(region_buy_ptot/region_buy_q,
                  region_buy_q,
                  color="red",
                  linestyle="--",
                  alpha=0.5,
                  label=f"{region} Demand")
            lines += RD

        claim_buy_df = buy_df[buy_df["claimEntityId"]==claim_id].reset_index(drop=True)
        if len(claim_buy_df) > 0:
            logging.info(f"Building {claim_name} demand curve.")
            claim_buy_q, claim_buy_ptot = price_line_builder(claim_buy_df)
            CD = ax0.plot(claim_buy_ptot/claim_buy_q,
                  claim_buy_q,
                  color="red",
                  linestyle=":",
                  lw=2,
                  path_effects=[pe.Stroke(linewidth=5, foreground='k'), pe.Normal()],
                  label=f"{claim_name} Demand")
            lines += CD

    if sell_df is not None:
        logging.info("Building global supply curve.")
        global_sell_q, global_sell_ptot = price_line_builder(sell_df)
        GS = ax0.plot(global_sell_ptot/global_sell_q,
                    global_sell_q,
                    color="blue",
                    alpha=0.2,
                    label="Global Supply")
        lines += GS

        region_sell_df = sell_df[sell_df["regionName"]==region].reset_index(drop=True)
        if len(region_sell_df) > 0:
            logging.info(f"Building {region} supply curve.")
            region_sell_q, region_sell_ptot = price_line_builder(region_sell_df)
            RS = ax0.plot(region_sell_ptot/region_sell_q,
                  region_sell_q,
                  color="blue",
                  linestyle="--",
                  alpha=0.5,
                  label=f"{region} Supply")
            lines += RS

        claim_sell_df = sell_df[sell_df["claimEntityId"]==claim_id].reset_index(drop=True)
        if len(claim_sell_df) > 0:
            logging.info(f"Building {claim_name} supply curve.")
            claim_sell_q, claim_sell_ptot = price_line_builder(claim_sell_df)
            CS = ax0.plot(claim_sell_ptot/claim_sell_q,
                        claim_sell_q,
                        color="blue",
                        linestyle=":",
                        lw=2,
                        path_effects=[pe.Stroke(linewidth=5, foreground='k'), pe.Normal()],
                        label=f"{claim_name} Supply")
            lines += CS

    # Formatting the plot
    ax0.set_ylim(bottom=0)
    ax0.grid(axis="y",visible=False)
    ax0.set_ylabel("Extant Order Quantity")
    ax0.ticklabel_format(axis="y",style="sci",scilimits=(0,0))
    ax0.get_yaxis().get_offset_text().set_position((-0.05,0.5))

    # ax1.set_ylim(bottom=0)
    # ax1.grid(axis="y",visible=False)
    # ax1.set_ylabel(f"{region} Quantity")
    # ax1.ticklabel_format(axis="y",style="sci",scilimits=(0,0))
    # ax1.get_yaxis().get_offset_text().set_position((1.05,0.5))

    # ax2.set_ylim(bottom=0)
    # ax2.grid(axis="y",visible=False)
    # ax2.set_ylabel(f"{claim_name} Quantity")
    # ax2.ticklabel_format(axis="y",style="sci",scilimits=(0,0))
    # ax2.get_yaxis().get_offset_text().set_position((1.15,0.5))
    
    plt.xlim(left=0)
    plt.title(f"{target_name} Supply and Demand\nClipper Capacity: {capacity:,}")
    plt.xlabel("Transaction-Averaged Price [Ħ]")

    labs = [l.get_label() for l in lines]
    plt.legend(lines, labs, loc='upper center', bbox_to_anchor=(0.5, 1.00),
          ncol=2, fancybox=True, shadow=True)
    
    plt.tight_layout()
    plt.show()

def price_line_builder(df):
    """
    Given a DataFrame of expected format and sorting,
    returns an immediately usable set of price lines.
    """
    q_bulk = df["quantity"].cumsum()
    p_ref = df["priceThreshold"]
    q = np.arange(0,df["quantity"].sum()+1)
    p_tot = np.zeros(len(q))
    for i in range(1,len(q)):
        if i%10000 == 0:
            logging.info(f"   - {np.round(100*i/len(q),2)}% done, {i:,}/{len(q):,}")
        k = np.where(q[i]<=q_bulk)[0][0]
        p_tot[i] = p_tot[i-1] + p_ref[k]
    return q, p_tot

class bitjita_client():
    """
    A client class for making queries to the Bitjita public API.
    """
    def __init__(self):
        self.base_url = "https://bitjita.com/api"

    def _make_request(self,endpoint,params=None):
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(
                url=url,
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Bitjita API Request failed: {e}")
            raise

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
    logging.info("===== BitCraft Supply-Demand Starting =====")
    main()
    logging.info("=== BitCraft Supply-Demand Shutting Down ===")
    logging.shutdown()