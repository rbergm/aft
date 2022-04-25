
library(readr)
library(tibble)
library(dplyr)

library(stringr)

library(ggplot2)
library(viridis)
library(ggallin)

read_df <- function(path_pattern, repetitions = 3, train = "full", cache = "on", fkeys = "off") {
  df_raw <- lapply(1:repetitions,
                   function(it) read_csv(str_glue(path_pattern), show_col_types = FALSE))
  for (i in 1:repetitions) {
    df_raw[[i]] <- df_raw[[i]] %>% add_column(run = i)
  }
  df <- bind_rows(df_raw) %>% mutate(t_exec = t_exec / 1000,
                                     train = train,
                                     cache = cache,
                                     fkeys = fkeys)
  return(df)
}

df_aqo <- read_df("pg-aqo/workloads/incremental/job-full-run-{it}-cout.csv")
df_bao <- bind_rows(
  read_df("pg-bao/workloads/job-full-train-run{it}-cout.csv"),
  read_df("pg-bao/workloads/job-small-train-run{it}-cout.csv", train = "small"),
  read_df("pg-bao/workloads/job-full-train-no-cache-run{it}-cout.csv", cache = "off"),
  read_df("pg-bao/workloads/job-full-train-fkeys-run{it}-cout.csv", fkeys = "on")
)

# PG-AQO base plot ----
df_plt <- df_aqo %>% group_by(run) %>% summarise(t_exec = sum(t_exec))
ggplot(df_plt, aes(x = factor(run), y = t_exec)) +
  geom_bar(stat = "identity", width = 0.4) +
  xlab("Run") +
  ylab("Execution time [seconds]") +
  theme_bw()
ggsave("shared/presentation/plots/aqo-bar-base.svg")

# PG-AQO outlier plot ----
q_out <- deframe(df_aqo %>% filter(t_exec == max(t_exec)) %>% select(label))
df_out <- df_aqo %>% filter(label == q_out) %>% select(run, t_exec)
df_plt <- df_aqo %>% group_by(run) %>% summarise(t_exec = sum(t_exec))
df_plt$runtime <- "Total"
df_out$runtime <- q_out
df_plt <- bind_rows(df_plt, df_out)

# Main outlier + total runtime (lineplot)
ggplot(df_plt, aes(x = factor(run), y = t_exec, group = runtime, colour = runtime)) +
  geom_point(aes(shape = runtime), size = 3) +
  geom_line(aes(linetype = runtime)) +
  xlab("Run") +
  ylab("Runtime [seconds, log10]") +
  scale_y_log10() +
  labs(fill = "") +
  theme_bw()
ggsave("shared/presentation/plots/aqo-line-main-outlier.svg")

# Main outlier + total runtime (barplot)
ggplot(df_plt, aes(x = factor(run), y = t_exec, fill = runtime)) +
  geom_bar(stat = "identity", position = "dodge") +
  xlab("Run") +
  ylab("Runtime [seconds, log10]") +
  scale_y_log10() +
  labs(fill = "Runtime") +
  scale_fill_viridis(discrete = TRUE, option = "cividis", direction = -1) +
  theme_bw()
ggsave("shared/presentation/plots/aqo-bar-main-outlier.svg")

# 90% outlier + total runtime (barplot)
df_out <- df_aqo %>%
  semi_join(df_aqo %>%
              filter(t_exec >= quantile(df_aqo$t_exec, 0.9), run == 3) %>%
              select(label, t_exec, run),
            by = c("label")) %>%
  select(run, label, t_exec) %>%
  group_by(run) %>%
  summarise(t_exec = sum(t_exec)) %>%
  mutate(runtime = "Outlier")
df_plt <- bind_rows(df_aqo %>%
                      group_by(run) %>%
                      summarise(t_exec = sum(t_exec)) %>%
                      mutate(runtime = "Total"),
                   df_out)
ggplot(df_plt, aes(x = factor(run), y = t_exec, fill = runtime)) +
  geom_bar(stat = "identity", position = "dodge") +
  xlab("Run") +
  ylab("Runtime [seconds, log10]") +
  scale_y_log10() +
  labs(fill = "Runtime") +
  scale_fill_viridis(discrete = TRUE, option = "cividis", direction = -1) +
  theme_bw()
ggsave("shared/presentation/plots/aqo-bar-quantile-outliers.svg")

# PG BAO base plot ----
df_plt <- df_bao %>%
  filter(cache == "on") %>%
  mutate(config = ifelse(train == "small",
                         "small, no FKs",
                         ifelse(fkeys == "on", "full, with FKs", "full, no FKs"))) %>%
  group_by(run, config) %>%
  summarise(t_exec = sum(t_exec))
ggplot(df_plt, aes(x = factor(run), y = t_exec, fill = config)) +
  geom_bar(stat = "identity", position = "dodge") +
  xlab("Run") +
  ylab("Runtime [seconds]") +
  labs(fill = "Setup") +
  scale_fill_viridis(discrete = TRUE, option = "cividis") +
  theme_bw()
ggsave("shared/presentation/plots/bao-bar-base.svg")

# PG BAO outlier plot ----
df_bao_base <- df_bao %>% filter(cache == "on", train == "full", fkeys == "off")
df_bao_rt_improv <- df_bao_base %>%
  filter(run == 1) %>%
  select(label, t_exec) %>%
  rename(t_exec_init = t_exec) %>%
  full_join(df_bao_base %>%
              filter(run == 3) %>%
              select(label, t_exec) %>%
              rename(t_exec_final = t_exec)) %>%
  mutate(t_exec_improv = t_exec_init / t_exec_final) %>%
  mutate(t_exec_weight = t_exec_improv * t_exec_final**2)
df_bao_out <- df_bao_base %>%
  semi_join(df_bao_rt_improv %>%
              filter(t_exec_improv > 1,
                     t_exec_weight >= quantile(t_exec_weight, 0.9)),
            by = "label")
df_plt <- bind_rows(
  df_bao_base %>% mutate(stat = "total"),
  df_bao_out %>% mutate(stat = "speedup")) %>%
  group_by(stat, run) %>%
  summarise(t_exec = sum(t_exec)) %>%
  arrange(desc(stat))
ggplot(df_plt, aes(x = factor(run), y = t_exec, fill = stat)) +
  geom_col(position = position_dodge2(reverse = TRUE, padding = 0)) +
  xlab("Run") +
  ylab("Runtime [seconds]") +
  labs(fill = "Runtime") +
  scale_fill_viridis(breaks = c("total", "speedup"), labels = c("total", "speedup\nqueries"),
                     discrete = TRUE,
                     option = "cividis", direction = -1) +
  theme_bw()
ggsave("shared/presentation/plots/bao-bar-quantile-outliers.svg")

# PG Bao improvemwent plot ----
df_bao_base <- df_bao %>% filter(train == "full", cache == "on", fkeys == "off")
df_plt <- df_bao_base %>%
  filter(run == 1) %>%
  select(label, t_exec) %>%
  rename(t_exec_init = t_exec) %>% full_join(
    df_bao_base %>%
      filter(run == 3) %>%
      select(label, t_exec) %>%
      rename(t_exec_final = t_exec),
    by = "label") %>%
  mutate(t_exec_diff = t_exec_init - t_exec_final) %>%
  mutate(change = ifelse(t_exec_diff > 0, "decrease", "increase")) %>%
  arrange(desc(t_exec_diff))
ggplot(df_plt, aes(x = 1:nrow(df_plt), y = t_exec_diff, fill = change, colour = change)) +
  geom_line(size = 0.7, linetype = "dotted") +
  geom_area() +
  xlab("JOB query (sorted)") +
  ylab("Runtime improvement [seconds]") +

  scale_fill_viridis(discrete = TRUE, option = "cividis") +
  scale_colour_viridis(discrete = TRUE, option = "inferno") +
  labs(fill = "Runtime change", colour = "Runtime change") +
  theme_bw() +
  theme(axis.text.x = element_blank())
ggsave("shared/presentation/plots/bao-area-diff.svg")

# PG Bao cache comparison ----
read_timing_df <- function(path, cache = "on") {
  df <- read_csv(path,
                 col_names = c("timestamp", "iteration", "duration"),
                 col_types = cols(timestamp = col_datetime(format = "%s"),
                                  iteration = col_integer(),
                                  duration = col_time())) %>%
    mutate(cache = cache)
  return(df)
}
df_bao_cache <- read_timing_df("pg-bao/workloads/timing-full-train.csv")
df_bao_nocache <- read_timing_df("pg-bao/workloads/timing-full-train-no-cache.csv", cache = "off")
df_plt <- bind_rows(df_bao_cache, df_bao_nocache)
ggplot(df_plt, aes(x = cache, y = duration, shape = cache)) +
  geom_point(size = 3) +
  xlab("Cache") +
  ylab("Duration [minutes]") +
  scale_colour_viridis(discrete = TRUE, option = "cividis") +
  theme_bw() +
  theme(legend.position = "")
ggsave("shared/presentation/plots/bao-scatter-cache.svg")

df_plt <- df_bao %>%
  filter(train == "full", fkeys == "off") %>%
  group_by(cache, run) %>%
  summarise(t_exec = sum(t_exec))
ggplot(df_plt, aes(x = factor(run), y = t_exec, fill = cache)) +
  geom_col(position = "dodge") +
  xlab("Run") +
  ylab("Runtime [seconds]") +
  labs(fill = "Cache between runs") +
  scale_fill_viridis(discrete = TRUE, option = "cividis") +
  theme_bw()
ggsave("shared/presentation/plots/bao-bar-cache.svg")


# Summary ----
df_ues <- tibble(
  run = 1:3,
  t_exec = read_csv("pg-bao/workloads/job-ues-cout.csv") %>%
    select(t_exec) %>%
    mutate(t_exec = t_exec / 1000) %>%
    sum(),
  system = "ues")
df_baseline  <- tibble(
  run = 1:3,
  t_exec = read_csv("pg-bao/workloads/job-baseline-cout.csv") %>%
    select(t_exec) %>%
    mutate(t_exec = t_exec / 1000) %>%
    sum(),
  system = "baseline")
df_const <- bind_rows(df_ues, df_baseline)
rt_ues <- df_ues %>% filter(run == 1) %>% select(t_exec) %>% deframe()
rt_baseline <- df_baseline %>% filter(run == 1) %>% select(t_exec) %>% deframe()
df_const_simple <- tibble(system = c("UES", "baseline"), t_exec = c(rt_ues, rt_baseline))
df_plt <- bind_rows(df_bao %>% filter(train == "full", cache == "on", fkeys == "off") %>% mutate(system = "BAO"),
                    df_aqo %>% mutate(system = "AQO")) %>%
  group_by(system, run) %>%
  summarise(t_exec = sum(t_exec))
ggplot(df_plt, aes(x = factor(run), y = t_exec, fill = system)) +
  geom_col(position = "dodge") +
  xlab("Run") +
  ylab("Runtime [seconds]") +
  scale_fill_viridis(discrete = TRUE, option = "cividis") +
  geom_hline(aes(yintercept = rt_ues, linetype = "UES", colour = "UES")) +
  geom_hline(aes(yintercept = rt_baseline, linetype = "baseline", colour = "baseline")) +
  labs(fill = "System", linetype = "", colour = "") +
  theme_bw()
ggsave("shared/presentation/plots/summary-bar.svg")

