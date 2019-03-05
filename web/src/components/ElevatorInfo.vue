<template>
  <v-container grid-list-lg>
    <h2>Current Floor {{current_floor}}</h2>
    <v-layout row wrap>

      <v-flex v-for="item in elevators" xs12 md6 lg4>

        <v-card
            :key="item.floor_num"
            class="my-3" color="accent">
          <v-card-title color="secondary">
            <div class="headline">Floor {{ item.floor_num }}</div>
            <v-container ma-0 pa-0>
              <v-layout row>
                <v-flex xs6>
                  <v-flex>
                    <v-btn :class="{ 'error': item.up_is_pressed }"
                           @click.native="control_elevator(item.floor_num, 0)">
                      <v-icon>fas fa-caret-up</v-icon>
                      UP
                    </v-btn>
                  </v-flex>
                  <v-flex>
                    <v-btn :class="{ 'error': item.down_is_pressed }"
                           @click.native="control_elevator(item.floor_num, 1)">
                      <v-icon>fas fa-caret-down</v-icon>
                      down
                    </v-btn>
                  </v-flex>
                </v-flex>
                <v-flex xs6 my-1>
                  <v-flex>
                    <v-icon x-large  :class="{ 'error--text': item.door_opened }" v-if="item.door_opened">
                      fas fa-door-open
                    </v-icon>
                    <v-icon x-large v-else>
                      fas fa-door-closed
                    </v-icon>
                  </v-flex>
                  <v-flex>
                    <v-icon  x-large  :class="{ 'error--text': item.rolling_door_opened }">fas fa-scroll</v-icon>
                  </v-flex>
                </v-flex>

              </v-layout>
            </v-container>
          </v-card-title>
          <br>
          <!--</v-hover>-->
          <!--<v-card-text color="primary">-->
          <!--&lt;!&ndash;<v-hover>&ndash;&gt;-->


          <!--</v-card-text>-->
          <!--<v-card-actions>-->
          <!--<v-btn>Share</v-btn>-->
          <!--<v-spacer></v-spacer>-->
          <!--<v-btn>Explore</v-btn>-->
          <!--</v-card-actions>-->
        </v-card>
      </v-flex>
    </v-layout>
  </v-container>
</template>

<script>
  import axios from 'axios';

  export default {
    name: "ElevatorInfo",
    data() {
      return {
        elevators: {},
        current_floor: 0
      }
    },
    created() {
      this.$options.sockets.onmessage = (data) => {
        var d = JSON.parse(data.data)
        d.key = data.timeStamp
        if ("status" in d) {
          this.current_floor = d.status.current_floor;
          this.elevators = d.status.floors;
        }
      }
    },
    methods: {
      control_elevator(floor, direct) {
        axios.get("dev/elevator/control",
          {
            params: {
              floor: floor,
              direct: direct
            }
          }).then(function () {
          console.log("control send to ${floor}, direct ${direct}")
        })
      }
    }
  }
</script>

<style scoped>
  .glow {
    text-shadow: 5px 5px 25px #FFFFFF;
  }
  .red_font {

  }
</style>