################################################################################
# Iterated singing with musicians (replication Anglada-Tort et al., 2023)
# Script: Analysis
################################################################################
# import libraries
library(tidyverse)
library(egg)
library(ggpubr)
library(cowplot)
library(viridis)

source("utils/plots.R")

# global parameters
loadNamespace("egg")
theme_set(theme_pubr())

MAX_INTERVAL_SIZE = 13
interval_range = c(-MAX_INTERVAL_SIZE,MAX_INTERVAL_SIZE)
vertical.lines = seq(from=min(interval_range), to=max(interval_range), by = 1)

interval_range_pitch = c(45,75)
vertical.lines_pitch = seq(from=min(interval_range_pitch), to=max(interval_range_pitch), by = 1)

# import data
data_melodies <- read_csv("data/clean-data/manu-test-ising1/data-test-ising1_full.csv") # pilot study
data_melodies <- read_csv("data/clean-data/singing-musicians-June-2026/singing-musicians-June-2026_full.csv") # first batch June 2026
data_melodies <- read_csv("data/clean-data/singing-musicians-July-2026/singing-musicians-July-2026_full.csv") # second batch July 2026

table(data_melodies$degree)
length(table(data_melodies$network_id))
length(table(data_melodies$participant_id))


################################################################################
# Analysis - error
################################################################################
# calculate the mean interval error over generations
error_data = data_melodies %>% 
  group_by(degree) %>% 
  summarise(
    n = n(), 
    mean_pitch_interval_error = mean(root_mean_squared_interval, na.rm = T),
    sd_pitch_interval_error = sd(root_mean_squared_interval, na.rm = T),
    se_pitch_interval_error = sd_pitch_interval_error/sqrt(n)
  )

# plot pitch interval error
plot_pitch_interval_error = error_data %>%
  ggplot(aes(x= degree, y = mean_pitch_interval_error)) + 
  geom_line()+
  geom_ribbon(aes(ymin=mean_pitch_interval_error - se_pitch_interval_error, 
                  ymax=mean_pitch_interval_error + se_pitch_interval_error),  
              alpha = 0.4)  +
  geom_point(size = 2, shape=21) +
  scale_x_continuous(breaks=c(1,2,3,4,5,6,7,8,9,10, 11)) +
  ylab("Copying Error (Pitch Interval)") +
  xlab("Iteration") +
  ggtitle("Pitch Interval Error") +
  theme_classic() +
  theme(legend.position = "none")

plot_pitch_interval_error

# save
# ggsave("evolution_pitcherror.png", width = 8, height = 8, units = "cm")


################################################################################
# Marginals
################################################################################
NBOOT = 1000
BW = 0.25

# marginals intervals
data_melodies_long_intervals =  data_melodies %>% 
  select(id:participant_id, sung_interval1:target_interval2) %>%
  pivot_longer(cols = starts_with("sung_interval"),
               names_to = "interval_pos",
               values_to = "interval")

marginals_melodies_intervals = make_marginals_kde(data_melodies_long_intervals, c("interval"), NBOOT, BW, "marginals") 

marginals_melodies_intervals

# save
# ggsave("results/marginals_intervals.png", width = 14, height = 7, units = "cm")

