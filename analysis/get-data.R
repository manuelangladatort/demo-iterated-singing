################################################################################
# Iterated singing with musicians (replication Anglada-Tort et al., 2023)
# Script: Prepare data from psynet export (13.1.1)
################################################################################
# imports
library(tidyverse)
library(egg)
library(ggpubr)

# methods
source("utils/utils.R")  # prepare data


# global parameters
set.seed(2024)
loadNamespace("egg")
theme_set(theme_pubr())

MAX_INTERVAL_SIZE <- 15
interval_range <- c(-MAX_INTERVAL_SIZE,MAX_INTERVAL_SIZE)
vertical.lines <- seq(from=min(interval_range), to=max(interval_range), by = 1)


################################################################################
# Pilot study (manu-test-ising1)
# 23 participants?
# 50 trials per person (within-participants: 5 chains, 10 iterations)
################################################################################
data_nodes <- read_csv("data/clean-data/manu-test-ising1/manu-test-ising1_node_data.csv")
data_trials <- read_csv("data/clean-data/manu-test-ising1/manu-test-ising1_trial_data.csv")

length(table(data_nodes$network_id))
table(data_nodes$degree)
length(table(data_trials$network_id))
length(table(data_trials$degree))

data_nets = prepare_trial_data(data_nodes[,-1], data_trials[,-1])

length(unique(data_nets$participant_id)) # 18
length(unique(data_nets$network_id)) # 85
table(data_nets$degree) 
table(data_nets$trial_maker_id)

data_nets <- data_nets %>% 
  mutate(trial_type = ifelse(degree != 0, "node_trial", "source_trial")) %>%
  select(-definition, -seed, -stats, -reason)

# save
data_nets %>% 
  rowwise() %>% 
  mutate_if(is.list, ~paste(unlist(.), collapse = ',')) %>% 
  write.csv("data/clean-data/manu-test-ising1/data-test-ising1_full.csv", row.names = FALSE)


################################################################################
# First batch musicians (singing-musicians-June-2026)
# 24 participants
# 50 trials per person (within-participants: 5 chains, 10 iterations)
# NOTE: experiment mostly worked but it needs to improve to avoid too many failed trials in one network
################################################################################
data_nodes <- read_csv("data/clean-data/singing-musicians-June-2026/singing-musicians-June-2026_node_data.csv")
data_trials <- read_csv("data/clean-data/singing-musicians-June-2026/singing-musicians-June-2026_trial_data.csv")

length(table(data_nodes$network_id))
table(data_nodes$degree)
length(table(data_trials$network_id))
length(table(data_trials$degree))

data_nets = prepare_trial_data(data_nodes[,-1], data_trials[,-1])

length(unique(data_nets$participant_id)) # 25
length(unique(data_nets$network_id)) # 125
table(data_nets$degree) 
table(data_nets$trial_maker_id)

data_nets <- data_nets %>% 
  mutate(trial_type = ifelse(degree != 0, "node_trial", "source_trial")) %>%
  select(-definition, -seed, -stats, -reason)

# save
data_nets %>% 
  rowwise() %>% 
  mutate_if(is.list, ~paste(unlist(.), collapse = ',')) %>% 
  write.csv("data/clean-data/singing-musicians-June-2026/singing-musicians-June-2026_full.csv", row.names = FALSE)


################################################################################
# Second batch musicians (singing-musicians-July-2026)
# 24 participants
# 50 trials per person (within-participants: 5 chains, 10 iterations)
# NOTE: experiment mostly worked but it needs to improve to avoid too many failed trials in one network
################################################################################
data_nodes <- read_csv("data/clean-data/singing-musicians-July-2026/singing-musicians-July-2026_node_data.csv")
data_trials <- read_csv("data/clean-data/singing-musicians-July-2026/singing-musicians-July-2026_trial_data.csv")

length(table(data_nodes$network_id))
table(data_nodes$degree)
length(table(data_trials$network_id))
length(table(data_trials$degree))

data_nets = prepare_trial_data(data_nodes[,-1], data_trials[,-1])

length(unique(data_nets$participant_id)) # 76
length(unique(data_nets$network_id)) # 348
table(data_nets$degree) 
table(data_nets$trial_maker_id)

data_nets <- data_nets %>% 
  mutate(trial_type = ifelse(degree != 0, "node_trial", "source_trial")) %>%
  select(-definition, -seed, -stats, -reason)

# save
data_nets %>% 
  rowwise() %>% 
  mutate_if(is.list, ~paste(unlist(.), collapse = ',')) %>% 
  write.csv("data/clean-data/singing-musicians-July-2026/singing-musicians-July-2026_full.csv", row.names = FALSE)
