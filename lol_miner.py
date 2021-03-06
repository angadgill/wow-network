"""
This script is used to mine data for League of Legends (LoL) using the API provided by RiotGames

The script takes two arguments: seed node (summonerId) and starting checkpoint num
For example:
    `python lol_miner.py 51666047 0` starts mining at summonerId 51666047 from checkpoint 0
     `python lol_miner.py 51666047 -1` starts mining at summonerId 51666047 from scratch (no checkpoints used)

Author: Angad Gill
"""

import networkx as nx
import time
from collections import deque
import sys

import utils
import algos
from lol import riot_games_api


# Parameters used in this script
MAX_HOP = 2  # stopping criteria for the Breadth First Search
TIME_SLEEP = 1.2  # seconds to wait between requests (roughly)
CHECKPOINT_INTERVAL = 10  # number of summonerIds after which to dump data to disk


def initialize(summonerId):
    """
    Initialize all data structures used in for this miner.

    Args:
        summonerId: seed node

    Returns:
        matches, discovered_summonerIds, g, max_hop, bfs_queue, hop
    """
    # Initialize -- Starting from seed
    matches = {}  # Store data for all matches
    discovered_summonerIds = {summonerId: True}  # Track discovered nodes
    discovered_matchIds = {}
    g = nx.Graph()

    max_hop = MAX_HOP  # Used as a stopping condition for Breadth First Search

    bfs_queue = deque([{'summonerId': summonerId, 'hop': 0}])  # Queue for breadth first search
    hop = 0

    return matches, discovered_summonerIds, discovered_matchIds, g, max_hop, bfs_queue, hop


def mine(checkpoint_num, matches, discovered_summonerIds, discovered_matchIds, g, max_hop, bfs_queue, hop):
    """
    Mine using Breadth First Search algorithm.

    Returns:
        no return
    """
    loop_count = 0  # used to track save points

    while (len(bfs_queue)>0) and (hop <= max_hop):

        loop_count += 1

        # Dequeue next summonerId
        next_item_in_queue = bfs_queue.popleft()
        summonerId = next_item_in_queue['summonerId']
        hop = next_item_in_queue['hop']

        # Get match ids for current node
        matchIds = rg.get_matchIds_by_summoner(summonerId)
        num_matches = len(matchIds)

        print ""
        print "SummonerId %d at hop %d has %d matches." % (summonerId, hop, num_matches)

        # Loop through all matches and add all members to the network
        for i, matchId in enumerate(matchIds):
            print "\rMatch %d out of %d [%0.1f%%]" % (i+1, num_matches, (i+1)/float(num_matches)*100),

            if matchId in discovered_matchIds:  # skip loop if match info already retreived
                continue

            # Get full match data and extract team members
            try:
                match = rg.get_match(matchId)
            except:
                print ""
                print "Error, skipping matchId: %d" % matchId
                continue

            team_memberIds = rg.get_summonerIds_by_match(match=match, team_with=summonerId)

            # Add team members to graph as a clique, with matchId info on edges
            g = algos.add_clique_with_weights(g, team_memberIds, edge_attr={'matchId': matchId})

            # Add new memberIds to queue
            for i in team_memberIds:
                if i not in discovered_summonerIds:
                    bfs_queue.append({'summonerId': i, 'hop': hop+1})
                    discovered_summonerIds[i] = True

            # Add match data to matches dict
            match = utils.list_of_dict_to_dict([match], 'matchId')
            matches.update(match)
            discovered_matchIds[matchId] = True

            # Sleep to stay under the API data rate limit
            time.sleep(TIME_SLEEP)

        if loop_count % CHECKPOINT_INTERVAL == 0:
            # Save data every CHECKPOINT_INTERVAL number of summonerIds
            checkpoint_num += 1
            utils.save_state(checkpoint_num, matches, discovered_summonerIds, discovered_matchIds, g, max_hop, bfs_queue, hop)
            return ""


if __name__ == '__main__':
    rg = riot_games_api.RiotGames('lol/riot_games_api.key')

    # Read parameters from terminal
    summonerId = int(sys.argv[1])
    checkpoint_num = int(sys.argv[2])

    print "Starting at summonerId %d and checkpoint num %d ..." % (summonerId, checkpoint_num)

    # Initialize or load checkpoint data
    if checkpoint_num == -1:
        matches, discovered_summonerIds, discovered_matchIds, g, max_hop, bfs_queue, hop = initialize(summonerId)
    else:
        matches, discovered_summonerIds, discovered_matchIds, g, max_hop, bfs_queue, hop = utils.load_state(checkpoint_num)

    # They call it a mine! A MINE!!
    mine(checkpoint_num, matches, discovered_summonerIds, discovered_matchIds, g, max_hop, bfs_queue, hop)
