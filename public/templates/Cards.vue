<template>
  <b-container>
    <div v-if="meals">
      <b-row>
        {{ meals}}waitwhat
        <!-- <div v-bind:key="data.index" v-for="data in meals">
          <b-col l="4">
            <b-card
              img-alt="Image"
              img-top
              tag="article"
              style="max-width: 20rem;"
              class="mb-2">
              <b-card-text>{{ `${data.strCategoryDescription.slice(0,100)}...` }}</b-card-text>
              <b-button href="#" variant="primary">View food</b-button>
            </b-card>
          </b-col> -->
        </div>
      </b-row>
    </div>
    <div v-else>
      <h5>No meals available yet</h5>
    </div>
  </b-container>
</template>

<script>
import axios from "axios";
export default {
  data() {
    return {
      meals: ['test']
    };
  }
  // mounted() {
  //   this.loader()
  //       .then(() => {
  //          this.component = () => this.loader()
  //       })
  //       .catch(() => {
  //          this.component = () => import('templates/default')
  //       })
  // }
  //,
  // mounted() {
  //   axios
  //     .get("https://www.themealdb.com/api/json/v1/1/categories.php")
  //     .then(response => {
  //       this.meals = response.data.categories;
  //     })
  //     .catch(err => {
  //       console.log(err);
  //     });
  // }
};
</script>
